/*
  AnalogReadSerial
  Reads an analog input on pins 0-8, prints the results to the serial monitor.
*/

// the setup routine runs once when you press reset:
void setup() {
  // initialize serial communication at 9600 bits per second:
  Serial.begin(9600);
}

// the loop routine runs over and over again forever:
void loop() {
  if (Serial.available() > 0) {
    char inByte = Serial.read();
      if (inByte =='0') {
          int sensorValue0 = analogRead(A0);
          Serial.println(sensorValue0);
          
          int sensorValue1 = analogRead(A1);
          Serial.println(sensorValue1);

          int sensorValue2 = analogRead(A2);
          Serial.println(sensorValue2);
          
          int sensorValue3 = analogRead(A3);
          Serial.println(sensorValue3);

          int sensorValue4 = analogRead(A4);
          Serial.println(sensorValue4);
          
          int sensorValue5 = analogRead(A5);
          Serial.println(sensorValue5);

          int sensorValue6 = analogRead(A6);
          Serial.println(sensorValue6);
          
          int sensorValue7 = analogRead(A7);
          Serial.println(sensorValue7);
         
          int sensorValue8 = analogRead(A8);
          Serial.println(sensorValue8); 
      } 
  }
}
