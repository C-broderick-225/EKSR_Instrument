// Custom setup file for the EKSR Instrument
// Setup for the ESP32 S3 with ILI9341 display
#define USER_SETUP_ID 400

// See SetupX_Template.h for all options available

#define ILI9341_DRIVER

#define TFT_WIDTH  240  // ST7789 240 x 240 and 240 x 320
#define TFT_HEIGHT 320  // ST7789 240 x 320

// Typical board default pins - change to match your board
#define TFT_CS   10   //     10 or 34 (FSPI CS0)
#define TFT_MOSI 11   //     11 or 35 (FSPI D)
#define TFT_SCLK 12   //     12 or 36 (FSPI CLK)
#define TFT_MISO 13   //     13 or 37 (FSPI Q)

// Use pins in range 0-31
#define TFT_DC    14
#define TFT_RST   21

// chose which fonts to load/use
#define LOAD_GLCD
#define LOAD_FONT2
#define LOAD_FONT4
#define LOAD_FONT6
#define LOAD_FONT7
#define LOAD_FONT8
#define LOAD_GFXFF

#define SMOOTH_FONT

// FSPI (or VSPI) port (SPI2) used unless following defined. HSPI port is (SPI3) on S3.
//#define USE_HSPI_PORT

#define SPI_FREQUENCY  40000000       // Maximum for ILI9341

#define SPI_READ_FREQUENCY  6000000   // 6 MHz is the maximum SPI read speed for the ST7789V

#define SPI_TOUCH_FREQUENCY 2500000
