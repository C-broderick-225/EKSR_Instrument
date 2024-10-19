# Firmware

This is the firmware for the EKSR Instrument.

Code is for an ESP32-S3, and compiled with the Arduino IDE 2.3.3

It requires the TFT_eSPI library which is available in the Library Manager within the IDE
To setup the correct display driver and GPIOs used, you need to edit the **`User_Setup_Select.h`** file in the **`Arduino/libraries/TFT_eSPI`** folder.

Change the line that says:\
`  #include <User_Setup.h>                 // Default setup is root library folder`\
to:\
`  #include <User_Setups/Setup400_EKSR.h>  // Setup file for ESP32-S3 configured for ILI9341`\

Then copy the Setup400_EKSR.h file to the **`Arduino/libraries/TFT_eSPI/User_Setups`** folder.


Also, you'll need the ESP32_ATouch library, which I have included here in the **`lib`** folder.
Simply move the **`ESP32_ATouch`** folder to your **`Arduino/libraries`** folder.
