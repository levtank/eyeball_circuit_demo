#!/usr/bin/local/python3

import os, sys, pygame as pg, numpy as np, random
from pygame import gfxdraw
from pygame.locals import *
from itertools import combinations, product
from PIL import Image, ImageFilter
import serial
from time import sleep

# flag for arduino
arduino_on = False

# -------------- general properties -------------- 

# screen size (pixels)
size = width, height = 1200, 700 

# screen color
bg_color = [255, 245, 216]

# how rapidly you update cell alpha (ms)
gfx_update_interval = 10 

# width of unpopulated display border (pixels)
border_width = 20 

# dimensions of total cell matrix
n_rows = 10
n_cols = 10
n_cells = n_rows*n_cols

# number of distinct tuned populations 
n_region_cols = 3
n_region_rows = 3
n_regions = n_region_cols * n_region_rows 
region_id = list(range(n_regions))
region_active = [False for i in region_id]

# number of response cells per population
n_tuned_cells = 10 

# range of random jitter for x,y coordinates
xjit = 10 
yjit = 10 

# maximum amount of alpha transparency increase 
max_alpha = 150

# photocell properties
light_threshold = 1000 
current_light = [1000 for i in region_id]
prev_light = [1 for i in region_id]
light_on = [False for i in region_id]

# -------------- cell properties -------------- 

# ms, how long cell spikes in response to stimulation
response_duration = list(range(700,900,50)) 

 # magnitude of alpha increase (speed of spike propagation)
spike_duration = 80

# ms, determines baseline firing rate
baseline_isi = list(range(5000,8000,100)) 

# ms, determines stim firing rate
stim_isi = list(range(300,400,10)) 

# ms, determines habituated stim firing rate
habituation_isi = list(range(800,1200,10)) 

# probability of spiking given stimulus
spike_prob = [i/100 for i in range(70,100,1)] 

# --------------------------------- cell class definition ---------------------------------  

class cellSprite(pg.sprite.Sprite):
    
    def __init__(self,location,response_duration,spike_duration,baseline_isi,stim_isi,habituation_isi,spike_prob):
        pg.sprite.Sprite.__init__(self)

        # create cell graphic
        cellSprite.cellpng = pg.image.load("cell.png"); self.cellpng = cellSprite.cellpng
        cellSprite.cellonpng = pg.image.load("cellon.png"); self.cellonpng = cellSprite.cellonpng

        rotation = random.choice(list(range(0,10,1)) + list(range(-10,0,1)))
        cell_size = random.choice([x/100 for x in range(20,50,1)])
        self.cellpng = pg.transform.rotozoom(cellSprite.cellpng,rotation,float(cell_size))
        self.cellonpng = pg.transform.rotozoom(cellSprite.cellonpng,rotation,float(cell_size))

        # create additional surface to blit cell surface onto (for alpha+fading to work)
        cellSprite.image = pg.Surface(self.cellpng.get_size(), depth=24)
        self.image = cellSprite.image
        self.rect = self.image.get_rect()
        self.rect.center = location
        self.image.fill(bg_color)
        self.image.set_colorkey(bg_color)        
        self.image.set_alpha(0)

        # animation/timing properties
        self.next_update_time = 0 # time to update cell alpha
        self.update_interval = gfx_update_interval # ms, how rapidly you update cell alpha
        self.next_spike_time = 0 # time to spike next
        self.stimfire = False # whether stimuation is on
        self.response_onset = 0 # time of stimulation onset
        self.initiate_stimfire = False # whether to initiate stim-dependent firing
        self.alpha_increase = True # whether to increase cell alpha 
        self.habituate = False

        # cell-specfic properties
        self.response_duration = response_duration # ms, how long cell spikes in response to stimulation
        self.spike_duration = spike_duration # magnitude of alpha increase, (speed of spike propagation)
        self.baseline_isi = baseline_isi # ms, baseline firing rate
        self.stim_isi = stim_isi # ms, stimulation firing rate
        self.habituation_isi = habituation_isi # ms, habituated stimulation firing rate
        self.spike_prob = spike_prob # probability of spiking given stimulus

    def monitor_cell(self, current_time):

        # wait until next spike time or start stim-dependent firing if stim is on
        if (self.next_spike_time < current_time) | self.initiate_stimfire:

            # initiate stimfire only once per stim 
            self.initiate_stimfire = False

            # initiate spike
            self.initiate_spike = True

            if self.initiate_spike:

                # initiate spike only once at a time
                self.initiate_spike = False

                # trigger alpha to change
                self.image.set_alpha(0)
                self.alpha_increase = True

                # set next spike time
                if self.stimfire:
                    self.next_spike_time = current_time + self.stim_isi
                elif self.habituate:
                    self.next_spike_time = current_time + self.habituation_isi
                else:
                    self.next_spike_time = current_time + self.baseline_isi

        # check if firing response period is over
        if (self.response_onset+self.response_duration) < current_time:
            self.stimfire = False

        # update alpha of cells every update_interval ms
        if self.next_update_time < current_time:

            # alpha will only be set to increase if the cell is set to fire, otherwise stuck at 0
            if self.alpha_increase:
                self.image.set_alpha(self.image.get_alpha()+self.spike_duration)

                # if cell hits max alpha, start decreasing
                if self.image.get_alpha() >= max_alpha:
                    self.alpha_increase = False

            # alpha decreases until at zero, and remains there until cell is to fire again
            elif self.alpha_increase == False:
                self.image.set_alpha(self.image.get_alpha()-self.spike_duration)
 
            # update time
            self.next_update_time = current_time + self.update_interval

# --------------------------------- function to generate possible coordinates for cell positions ---------------------------------  

def generate_coords(width,height,border_width,n_rows,n_cols):

    step_x = int((width-(2*border_width))/n_cols)
    step_y = int((height-(2*border_width))/n_rows)

    xlocs = list(range(border_width,width-border_width+1,step_x))
    ylocs = list(range(border_width,height-border_width+1,step_y))

    # create coordinate pairs
    coords = list(product(xlocs,ylocs))
   
    # shift every other row to minimize blank space
    coords = [(i[0]+40,i[1]) if i[1] in ylocs[1::2] else i for i in coords]

    # jitter each location slightly 
    coords = [(i[0]+(np.random.randint(-xjit,xjit)),i[1]+(np.random.randint(-yjit,yjit))) for i in coords]

    return coords

# --------------------------------- function to choose tuned cells --------------------------------- 

def select_tuned_cells(cell_loc,width,border_width,n_region_cols,n_region_rows,n_tuned_cells):

    region_width = int((width-(2*border_width))/n_region_cols)
    region_height = int((height-(2*border_width))/n_region_rows)

    start_x, start_y = 0,0; tuned_pop = []

    for i in list(range(n_region_cols*n_region_rows)):
       
        region_xlim = [start_x+border_width,start_x+border_width+region_width]
        region_ylim = [start_y+border_width,start_y+border_width+region_height]
        print(region_xlim)
        print(region_ylim)
        cells_in_region =[cell[0] for cell in cell_loc if 
            (cell[:][1][0] > region_xlim[0]) & 
            (cell[:][1][0] < region_xlim[1]) & 
            (cell[:][1][1] > region_ylim[0]) & 
            (cell[:][1][1] < region_ylim[1])]

        # get only max number of required cells in each region
        if len(cells_in_region) > n_tuned_cells:
            tuned_cells = cells_in_region[0:n_tuned_cells]
        else:
            tuned_cells = cells_in_region

        tuned_pop.append(tuned_cells)

        # update start positions 
        start_x += region_width
        if (start_x/region_width)%n_region_cols == 0:
            start_x = 0
            start_y += region_height

    print(tuned_pop)       
    return tuned_pop

# --------------------------------- functions to activate a population --------------------------------- 

def control_region(region_number,action):

    for i,k in enumerate(tuned_cells[region_number]):

        if action == "activate":

            region_active[region_number] = True
            population[k].stimfire = True

            if population[k].spike_prob > np.random.rand(1):
                population[k].initiate_stimfire = True
                population[k].response_onset = pg.time.get_ticks() 

        elif action == "habituate":

            if ~population[k].stimfire:
                population[k].habituate = True

        elif action == "inactivate":
            region_active[region_number] = False
            population[k].habituate = False


def read_sensor(prev_light,current_light,light_on):

    # save previous light value
    prev_light = current_light

    # get current light value
    current_light = [int(i) for i in arduino.read(100).decode().splitlines()]

    # loop over sensors and update status
    for i,sensor in enumerate(current_light):

        if (sensor > light_threshold) & (~region_active[i]):
            light_on[i] = True
            control_region(region_id[i],"activate")

        elif (sensor > light_threshold) & light_on[i]:
            control_region(region_id[i],"habituate")

        elif (sensor < light_threshold) & (light_on[i]):
            control_region(region_id[i],"inactivate")
            light_on[i] = False
    
    return [prev_light,current_light,light_on]

# --------------------------------- create cells ---------------------------------  

population,cell_loc = [],[]

# create coordinates
locs = generate_coords(width,height,border_width,n_rows-1,n_cols-1)

for i in list(range(n_cells)):

    print("Creating cell %d" % i)

    # add to location list
    cell_loc.append((i,locs[i]))
    
    # create cells
    population.append(cellSprite(
            [locs[i][0],locs[i][1]],
            random.choice(response_duration),
            spike_duration,
            random.choice(baseline_isi),
            random.choice(stim_isi),
            random.choice(habituation_isi),
            random.choice(spike_prob)))

# choose tuned cells out of population
tuned_cells = select_tuned_cells(cell_loc,width,border_width,n_region_cols,n_region_rows,n_tuned_cells)

# ---------------------------------  main display loop --------------------------------- 

# start serial comm with arduino 
if arduino_on:
    arduino = serial.Serial('/dev/tty.usbmodem1411', baudrate = 9600, timeout = 0.01)
    sleep(1.5)

# initiate pygame 
screen = pg.display.set_mode(size) # pg.FULLSCREEN include FULLSCREEN arg if needed

pg.init()  

# main loop

while True:
    startloop = pg.time.get_ticks()
    # send 'read' msg to arduino
    if arduino_on:
        arduino.write(str.encode('0'))
  
    # check for keyboard input
    for event in pg.event.get():
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                if arduino_on: 
                    arduino.close()
                pg.quit()
            
            # monitor regions
            for i in list(range(n_regions)):
                if event.key == getattr(pg, 'K_%d' % i): 
                    control_region(i,"activate")    
    # blank the screen
    screen.fill(bg_color) 

    # get current time
    time = pg.time.get_ticks()

    # update display/cells on each iteration
    stimfire_cells = []

    for cell in population:

        # update cell timing
        cell.monitor_cell(time)

        # check which cells currently active
        stimfire_cells.append(cell.stimfire)

        # add cell image to display
        screen.blit(cell.cellpng,cell.rect)

        # add cell firing overlay to holding surface
        cell.image.blit(cell.cellonpng,(0,0))

        # add entire holding surface to display
        screen.blit(cell.image,cell.rect)
        

    # update screen
    pg.display.update()

    # update light levels 
    if arduino_on:
        prev_light,current_light,light_on = read_sensor(prev_light,current_light,light_on)

    print(pg.time.get_ticks() - startloop)
