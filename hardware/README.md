# Hardware for the EKSR Instrument.

The circuit is pretty straightforward.

The 12V input is dropped to 3.3V by an Alpha & Omega AOZ1284PI buck converter.

The ESP32-S3 controls the ILI9341 based TFT display though SPI and get touch data from the resistive touchcreen, using 4 ADC inputs.

The backlight is controlled with PWM through a N-channel FET.

Rev B adds a input voltage monitor though a 16:1 resistor divider, giving 900mV at 14.4V in.

Programming and log data output is, as usual for the ESP32's, through a 3.3V TTL level serial port.

Communication with the controller is though the built-in BLE in the ESP32-S3 (using Nimble BLE stack).


The board fits into a SZOMK AK-H-15 enclosure.\
This is not the enclosure used for the prototype, but it's the same inner dimensions and have an improved water seal.\
Still, the display have to be sealed against the enclosure, perhaps using a cutout "gasket" from 0.5mm rubber or silicone.

The `.brd` and `.sch` files in the `Fusion Files` folder, is EAGLE V9.x format.\
Project is originally made with Fusion 360/Fusion Electronics.
