# EKSR_Instrument (Fork)

**This repository is a fork of the original [EKSR_Instrument](https://github.com/original-author/EKSR_Instrument) project.**

This fork is being developed as the foundation for a new product that will rely heavily on the original EKSR_Instrument hardware and firmware. All credit for the initial design and implementation goes to the original author. This fork will introduce new features, modifications, and documentation specific to the goals of the new product.

---

Documentation on hardware and firmware for EKSR Instrument, a TFT display for FarDriver Motor Controllers


I started the EKSR_Instrument project as I needed a display for my homebuilt e-bike.

It uses an ESP32-S3 microcontroller to receive and decode messages from the Fardriver controller over a BLE link.

Data is then massaged into proper form and displayed on a 2.4" TFT display.

The display has a touchscreen, which allow various pages to be shown with Trip totals, Settings e.t.c.

The display looks like this: (sorry for bad reflections, I'll try get better photos)
![Display](/media/EKSR_display.jpg)


I've included a very short movie of the display in action, but it cannot be shown here on GitHub. You'll find it in the `/media` folder.


And finally the bike it's installed on:
![Bike](/media/EKSR_bike.jpg)

For those interested, this is an electric conversion of a Kawasaki KSR150, with a Fardriver ND96530 controller, a QS138 90H motor and a 96V 48Ah battery.

Specs are 140+ km/h top speed, 0-100 km/h in less than 3 seconds and a range of about 80 km.
