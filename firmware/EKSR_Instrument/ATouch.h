
#include <Arduino.h>
//#include <TFT_eSPI.h>

typedef enum measurement {
  MEASURE_X,
  MEASURE_Y
} measurement;

// GPIO Connections
#define IO_XL   2
#define IO_YU   1
#define IO_XR   3
#define IO_YD   4

class ATouch {

 public:
//  bool  begin(TFT_eSPI *pTFT_eSPI);

  void  selectMeasurement(measurement m);


           // Get raw x,y ADC values from touch controller
  uint8_t  getTouchRaw(uint16_t *x, uint16_t *y);
           // Get raw z (i.e. pressure) ADC value from touch controller
  uint16_t getTouchRawZ(void);
           // Convert raw x,y values to calibrated and correctly rotated screen coordinates
  void     convertRawXY(uint16_t *x, uint16_t *y);
           // Get the screen touch coordinates, returns true if screen has been touched
           // if the touch coordinates are off screen then x and y are not updated
           // The returned value can be treated as a bool type, false or 0 means touch not detected
           // In future the function may return an 8 "quality" (jitter) value.
  uint8_t  getTouch(uint16_t *x, uint16_t *y, uint16_t threshold = 600);

           // Run screen calibration and test, report calibration values to the serial port
  void     calibrateTouch(uint16_t *data, uint32_t color_fg, uint32_t color_bg, uint8_t size);
           // Set the screen calibration values
  void     setTouch(uint16_t *data);

 private:
  uint16_t _width = 240;
  uint16_t _height = 320;
 // TFT_eSPI *_TFT_eSPI;

           // Private function to validate a touch, allow settle time and reduce spurious coordinates
  uint8_t  validTouch(uint16_t *x, uint16_t *y, uint16_t threshold = 600);

           // Initialise with example calibration values so processor does not crash if setTouch() not called in setup()
  uint16_t touchCalibration_x0 = 800, touchCalibration_x1 = 2500, touchCalibration_y0 = 500, touchCalibration_y1 = 3000;
  uint8_t  touchCalibration_rotate = 0, touchCalibration_invert_x = 0, touchCalibration_invert_y = 0;

  uint32_t _pressTime;        // Press and hold time-out
  uint16_t _pressX, _pressY;  // For future use (last sampled calibrated coordinates)

};
