# eyeball_circuit_demo

Python and Arduino code for an interactive visualisation of sensory coding within the visual system. 

![eyeball](https://github.com/levtank/eyeball_circuit_demo/raw/master/desc_image.png)

see [here](https://levtank.github.io/osf-2016/) for more details about the concept. 

Light-level information is converted to voltage via photocell resistors (the "retina"), which is then converted to neural population responses (visualised neural firing in the "visual cortex"). The neural population responses are spatially organised to mirror that of the photocell arrangement (roughly "retinotopically").  

Photocell resistor information (voltage) is read into the computer via an Arduino Mega (which performs the analog-to-digital conversion) and is retrieved from the USB port in Python via pySerial. Light-level information is then converted to visualised neural responses in Python according to some basic, illustrative rules (used parameters are NOT meant to be biophysically plausable). 

Visualisation in Python uses pygame. 

Note that this is the first time that I use pygame and Arduino, so code may be sub-optimal. 
 
