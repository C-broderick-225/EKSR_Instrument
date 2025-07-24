
/*
  Code for the EKSR Instrument.
  Communicates with the FarDriver ND96530 Controller via Bluetooth BLE
  Displays data on a 240x320 pixel TFT display.

  Jesper Hansen, June 2022
  Various updates, October 2024

  Project home: https://github.com/magicmicros/EKSR_Instrument
  
*/


#define USE_NIMBLE  1

// uncomment this to include functions for message debugging on screen
//#define ON_SCREEN_MSG_DEBUG 1


#if USE_NIMBLE
#include "nimble.h"
#endif


#include <Preferences.h>
Preferences preferences;

#include "Free_Fonts.h"     // Include the header file attached to this sketch
#include "NotoSansBold36.h" // Font attached to this sketch
#define AA_FONT_LARGE NotoSansBold36


// Analog touch input
#include <ATouch.h>
ATouch AT;

// TFT class and vars
#include <TFT_eSPI.h>                   // Master copy here: https://github.com/Bodmer/TFT_eSPI
TFT_eSPI tft = TFT_eSPI();              // Invoke library, pins defined in User_Setup_Select.h
TFT_eSprite spr = TFT_eSprite(&tft);    // Sprite for meter reading
TFT_eSprite vspr = TFT_eSprite(&tft);   // Sprite for voltage

uint16_t  spr_width = 0;
uint16_t  vspr_width = 0;

typedef enum {
  AS_CONNECTING,
  AS_MAIN,
  AS_ODOMETER,
  AS_SETTINGS,  
} active_screen_e;

active_screen_e active_screen = AS_MAIN;  // Screen currently being displayed


class controller_data {
public:
  volatile uint16_t throttle;
  volatile uint8_t  gear;
  volatile uint16_t rpm;
  volatile float    controller_temp;
  volatile float    motor_temp;
  volatile float    speed;
  volatile float    power;
  volatile float    voltage;
};

controller_data ctr_data;


volatile float backlight = 50;


// Limits for battery stack display and power bar
float low_batt_limit = 86;
float high_batt_limit = 96;
float max_power = 20;

//
// wheel circumference
// adapt this to fit your bike
//
float wheel_circumference = 1.350;    // actual circumference, non-loaded is 1520mm  

#if ON_SCREEN_MSG_DEBUG
// storage for incoming messages
uint8_t message_store[30][12];
#endif


// states for connection status ISM
typedef enum  {
  CS_SEARCHING,
  CS_CONNECTED,
  CS_DISCONNECTED,
}connection_state_e;
connection_state_e connection_state = CS_SEARCHING;






/*********************************************************/

void ui_switch(void) {
  switch (active_screen) {
    case AS_CONNECTING:
      break;
    case AS_MAIN:
      active_screen = AS_ODOMETER;
      odometer_screen_init();
      break;
    case AS_ODOMETER:
      active_screen = AS_SETTINGS;
      settings_screen_init();
      break;
    case AS_SETTINGS:
      active_screen = AS_MAIN;
      main_screen_init();
      break;
  }  
}


void ui_update(void) {
  switch (active_screen) {
    case AS_CONNECTING:
      break;
    case AS_MAIN:
      main_screen_update();
      break;
    case AS_ODOMETER:
      odometer_screen_update();
      break;
    case AS_SETTINGS:
      settings_screen_update();
      break;
  }
}



/*********************************************************/

//
// Touch Field Class
//
class Field {
public:
  Field(int x, int y, int w, int h) { _x = x; _y = y; _w = w; _h = h; }
  bool hit();
protected:
  int _x, _y, _w, _h;
};


bool Field::hit() {
  uint16_t x,y;
  if ((AT.getTouch(&x,&y)) > 0) {
    printf("touch at %d,%d\r\n", x, y);  
  
    if ((x > _x) && (x < (_x + _w)) &&
      (y > _y) && (y < (_y + _h))) {
        printf("field hit at %d,%d\r\n", x, y);  
        return true;
      }
  }
  return false; 
}

/*********************************************************/

//
// Button Class
//
class Button : public Field {
public:
  Button(int x, int y, int w, int h, const char *txt, const GFXfont* font = FSS12);
  void draw();
private:
  String _text;
  const GFXfont* _font;  
};

Button::Button(int x, int y, int w, int h, const char *txt, const GFXfont* font) : Field(x,y,w,h) {
  _text = String(txt);
  _font = font;
}

void Button::draw() {

  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextDatum(MC_DATUM);
  tft.setFreeFont(_font);
  tft.drawString(_text.c_str(), _x + _w / 2,  _y + _h / 2);
  tft.drawRect(_x, _y, _w, _h, TFT_WHITE);
}

/*********************************************************/



//
// general touch fields
//
Field fNext(0, 0, 240, 40);

//
// odometer touch fields
//
Button bTotal(  0, 280, 80, 40, "Total");
Button bTrip1( 80, 280, 80, 40, "Trip1");
Button bTrip2(160, 280, 80, 40, "Trip2");
Button bReset(70, 200, 100, 40, "Reset");





/*****************************************************************************************************/
/*****************************************************************************************************/
/*****************************************************************************************************/

/*
    Total km , speed, power
    Trip 1 km , speed, power
    Trip 2 , speed, power

    km per kW
    
    Later, can perhaps add estimated range?  
 */  

//
// Odometer Class
//
class Odometer {
public:
  Odometer(const char *label, bool can_reset = false);
  void update_distance(float distance);
  void update_speed(float speed);
  void update_power(float power);
  void draw();
  void load();
  void save();
  void reset();
//private:
  String _label;
  
  bool   _can_reset;
  float  _distance;
  float  _speed;
  float  _power;
  float  _last_distance;
  float  _last_speed;
  float  _last_power;
};

Odometer::Odometer(const char *label, bool can_reset) {
  _label = String(label);
  _can_reset = can_reset;
  load();
}

void Odometer::update_distance(float distance) {
  _distance += distance;  
}

void Odometer::update_speed(float speed) {
  if (speed > _speed)
    _speed = speed;  
}

void Odometer::update_power(float power) {
  if (power > _power)
    _power = power;  
}

void Odometer::draw() {  
  bool isTotal = false;
  if (!_can_reset)   // sneaky way to determine if this is the Total page
    isTotal = true;

  tft.setTextDatum(TC_DATUM);
  tft.drawString(_label, 120, 40);

  tft.setTextDatum(TL_DATUM);
  tft.drawString("Distance", 0, 80);
  tft.drawString("Speed", 0, 120);
  tft.drawString("Power", 0, 160);

  if (isTotal)
    tft.drawString("km/kW", 0, 200);


  tft.setTextDatum(TR_DATUM);
  tft.drawFloat(_distance, 1, 195, 80);
  tft.drawFloat(_speed, 1, 195, 120);
  tft.drawFloat(_power, 1, 195, 160);
  if (isTotal) {
    float kmkw = 0;  

    // need power consumtion for this
    tft.drawFloat(kmkw, 1, 195, 200);
  }

  tft.setFreeFont(FSS9);  
  tft.setTextDatum(TL_DATUM);
  tft.setTextPadding(tft.textWidth("77"));
  tft.drawString("km", 200, 83);
  tft.setTextPadding(tft.textWidth("777"));
  tft.drawString("km/h", 200, 123);
  tft.setTextPadding(tft.textWidth("77"));
  tft.drawString("kW", 200, 163);


  // draw buttons
  bTotal.draw();
  bTrip1.draw();
  bTrip2.draw();

  if (_can_reset)   // sneaky way to determine if this isn't the Total page
    bReset.draw();  // only draw reset button on trip pages
}


void Odometer::load() {
  _distance = _last_distance = preferences.getULong((_label + String("_km")).c_str(), 0) / 10.0; 
  _speed = _last_speed = preferences.getULong((_label + String("_speed")).c_str(), 0) / 10.0; 
  _power = _last_power = preferences.getULong((_label + String("_power")).c_str(), 0) / 10.0;
}

void Odometer::save() {
  preferences.getULong((_label + String("_km")).c_str(), _distance * 10.0);
  preferences.getULong((_label + String("_speed")).c_str(), _speed * 10.0);
  preferences.getULong((_label + String("_power")).c_str(), _power * 10.0);
  _last_distance = _distance;
  _last_speed = _speed;
  _last_power = _power;
}

void Odometer::reset() {
  if (_can_reset) {  
    _distance = _last_distance = 0; 
    _speed = _last_speed = 0; 
    _power = _last_power = 0;
    save();
  }
}

/*********************************************************/

Odometer odo_total("Total");
Odometer odo_trip1("Trip1", true);
Odometer odo_trip2("Trip2", true);
Odometer *current_odo = &odo_total;



/*****************************************************************************************************/
/*****************************************************************************************************/
/*****************************************************************************************************/

void setup() {
  Serial.begin(115200);
  Serial.println("EKSR Instrument");

  // open up preferences
  preferences.begin("my-app", false); 

  Serial.println("Init TFT");
  // Initialise the screen
  tft.init();
  // set portrait orientation
  tft.setRotation(0);

  // start up Nimble
#if USE_NIMBLE
  active_screen = AS_CONNECTING;
  start_screen_init();            // spinner screen
  Serial.println("Start NIMBLE");
  nimble_start();   
#else
  active_screen = AS_MAIN;
  main_screen_init();             // main screen
#endif


  // setup PWM output on GPIO9
  pinMode(9, OUTPUT);
  digitalWrite(9, HIGH);
  // configure LED PWM functionalities (Arduino-ESP32 3.0+ syntax)
  ledcAttachChannel(9, 5000, 8, 0); // pin, freq, resolution, channel
  // set duty cycle (0-255 for 8 bits)
  ledcWrite(9, 100);


  Serial.println("Started");
}

/*****************************************************************************************************/
/*****************************************************************************************************/
/*****************************************************************************************************/

void loop() {
  static uint32_t lastMillis;
  static int active = 0;
  uint16_t x, y;


#if USE_NIMBLE

  switch (connection_state) {
    case CS_SEARCHING:
      spinner(120,200, active);
      active += 30;
      active %= 360;
      delay(50);
      if (service_found) {
        if (connectToServer()) {
          is_connected = true;
          service_found = false;    
          connection_state = CS_CONNECTED;
          active_screen = AS_MAIN;
          main_screen_init();
          odo_trip2.reset();        // auto-reset TRIP2
        }
        else
          connection_state = CS_DISCONNECTED;
      }
      break;
      
    case CS_CONNECTED:
      if (!is_connected)
          connection_state = CS_DISCONNECTED;
      break;
      
    case CS_DISCONNECTED:
      preferences.end();
      Serial.println("Failed to connect or disconnected... Restarting");
      ESP.restart();
      break;
  }


  if (!is_connected && !service_found) {
    spinner(120,200, active);
    active += 30;
    active %= 360;
    delay(50);  
    return;
  }

  if (connection_state == CS_CONNECTED) {
    uint8_t buffer[] = { 0xAA, 0x13, 0xec, 0x07, 0x01, 0xF1, 0xA2, 0x5D };
    uint32_t currentMillis = millis();
    if (currentMillis - lastMillis >= 2000) {
      lastMillis = currentMillis;
    // send a keep-alive packet every 2 seconds   
    if (!nimble_send(buffer, 8))
        Serial.println("    Write Failed *****************************");
    } 
#else
   if (1) {
#endif
    /*********************************************************/

#if ON_SCREEN_MSG_DEBUG
  debug_packets();
#else

    //  driving at 60km/h, each 1km interval every 60 seconds (60 times per hour), 100m every 6 seconds (600 times per hour)
    //
    // only update odometer every 100m
    // and only save if rpm > 0 to avoid saving at power off time
    //    
    if (((odo_total._distance - odo_total._last_distance) > 100) && (ctr_data.rpm > 0)) {    
      odo_total.save();
      odo_trip1.save();
      odo_trip2.save();
    }

#endif
  }


  if (fNext.hit()) {    // check if there is a touch on the main UI switch field
      ui_switch();      // if so, switch to next UI
  }

  ui_update();
}



/*****************************************************************************************************/
/*****************************************************************************************************/
/*****************************************************************************************************/


void odometer_screen_init(void) {

  tft.fillScreen(TFT_BLACK);
  tft.setFreeFont(FSS12);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextDatum(TC_DATUM);
  tft.drawString("Odometer", 120, 5);

  // draw current screen
  current_odo->draw();  
}

void odometer_screen_update(void) {
  Odometer *pold = current_odo;
  
  // check touch on buttons
  if (bTotal.hit())
    current_odo = &odo_total;
  if (bTrip1.hit())
    current_odo = &odo_trip1;
  if (bTrip2.hit())
    current_odo = &odo_trip2;

  // check for reset
  if (bReset.hit())
    current_odo->reset();
 
  // if any change 
  if (current_odo != pold) {
    odometer_screen_init();   //redraw
  }
}



/*****************************************************************************************************/
/*****************************************************************************************************/
/*****************************************************************************************************/



void settings_screen_init(void) {
/*
    backlight
    low batt
    high batt
    max power
    wheel circumference or better - calibrate to known speed  
 */  

  tft.fillScreen(TFT_BLACK);
  tft.setFreeFont(FSS12);
//  tft.setTextFont(2);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextDatum(TC_DATUM);
  tft.drawString("Settings", 120, 5);
//  tft.setTextPadding(tft.textWidth("7777777777777"));

  tft.setTextDatum(TL_DATUM);
  tft.drawString("Backlight", 0, 80);
  tft.drawString("Low Batt", 0, 120);
  tft.drawString("High Batt", 0, 160);
  tft.drawString("Max Power", 0, 200);
  tft.drawString("Wheel circ.", 0, 240);

  tft.setTextPadding(tft.textWidth("77777"));

  tft.setTextDatum(TR_DATUM);
  tft.drawFloat(backlight, 1, 195, 80);
  tft.drawFloat(low_batt_limit, 1, 195, 120);
  tft.drawFloat(high_batt_limit, 1, 195, 160);
  tft.drawFloat(max_power, 1, 195, 200);
  tft.drawFloat(wheel_circumference, 2, 195, 240);

}

void settings_screen_update(void) {

  tft.setTextDatum(TR_DATUM);
  tft.drawFloat(backlight, 1, 195, 80);
  tft.drawFloat(low_batt_limit, 1, 195, 120);
  tft.drawFloat(high_batt_limit, 1, 195, 160);
  tft.drawFloat(max_power, 1, 195, 200);
  tft.drawFloat(wheel_circumference, 2, 195, 240);


}

/*****************************************************************************************************/
/*****************************************************************************************************/
/*****************************************************************************************************/


void start_screen_init(void) {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextDatum(ML_DATUM);
  tft.drawString("Connecting", 50, 160, 4);
}


/*********************************************************/

void main_screen_init(void) {
  tft.fillScreen(TFT_BLACK);

  // Plot the label text
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextDatum(MC_DATUM);
  tft.drawString("kW", 120, 70, 4);


  // Load the font and create the Sprite for reporting the value
  spr.loadFont(AA_FONT_LARGE);
  spr_width = spr.textWidth("7777"); // 7 is widest numeral in this font
  spr.createSprite(spr_width, spr.fontHeight());
  spr.fillSprite(TFT_BLACK);
  spr.setTextColor(TFT_WHITE, TFT_BLACK, true);
  spr.setTextDatum(MC_DATUM);
  spr.setTextPadding(spr_width);


  // Plot the label text
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextDatum(ML_DATUM);
  tft.drawString("Battery Voltage", 20, 275, 2);

  tft.drawRect(0, 285, 137, 34, TFT_WHITE);



  // Load the font and create the Sprite for reporting the voltage
  vspr.loadFont(AA_FONT_LARGE);
  vspr_width = vspr.textWidth("77777"); // 7 is widest numeral in this font
  vspr.createSprite(vspr_width, vspr.fontHeight());
  vspr.fillSprite(TFT_BLACK);
  vspr.setTextColor(TFT_WHITE, TFT_BLACK, true);
  vspr.setTextDatum(MC_DATUM);
  vspr.setTextPadding(vspr_width);


  // Plot label texts
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextDatum(ML_DATUM);
  tft.drawString("Motor Temperature", 10, 135, 2);
  tft.drawString("Controller Temp", 10, 160, 2);

  tft.drawString("RPM", 10, 185, 2);

  // rpm rect
  tft.drawRect(10, 200, 220, 14, TFT_WHITE);

  tft.drawString("Speed", 10, 245, 4);

  tft.drawString("Gear", 210, 35, 2);

  // thottle rect
  tft.drawRect(228, 219, 12, 62, TFT_WHITE);
}


void main_screen_update(void) {
  show_motor_temp();
  show_controller_temp();
  show_rpm();
  show_speed();
  show_power();
  show_battery();
  show_gear();
  show_throttle();
}


/*****************************************************************************************************/
/*****************************************************************************************************/
/*****************************************************************************************************/

void show_power() {

  // Draw a segmented ring meter type display
  // Centre of screen
  int cx = tft.width()  / 2;
  int cy = 105; //tft.height() / 2;

  // Inner and outer radius of ring
  float r1 = 80.0;
  float r2 = 100.0;

  // Inner and outer line width
  int w1 = r1 / 25;
  int w2 = r2 / 20;

  // The following will be updated by the getCoord function
  float px1 = 0.0;
  float py1 = 0.0;
  float px2 = 0.0;
  float py2 = 0.0;

  // angle for current power
  // 20kW at max
  int curpow = -90 + (int) (180.0 * fabs(ctr_data.power) / 20.0);

  //Serial.println(curpow);
  //curpow = -90;

  // Wedge line function, an anti-aliased wide line between 2 points, with different
  // line widths at the two ends. Background colour is black.
  for (int angle = -90; angle <= 90; angle += 10) {
    getCoord(cx, cy, &px1, &py1, &px2, &py2, r1, r2, angle);
    uint16_t color = rainbow(map(angle, -90, 90, 64, 127));
    if (angle >= curpow) color = 0b0101001010001010;
    tft.drawWedgeLine(px1, py1, px2, py2, w1, w2, color, TFT_BLACK);
  }

  // Update the number at the centre of the dial
  if (ctr_data.power == 0)
    spr.setTextColor(TFT_WHITE, TFT_BLACK, true); // idle, white
  else if (ctr_data.power < 0)
    spr.setTextColor(TFT_GREEN, TFT_BLACK, true); // driving power, green
  else
    spr.setTextColor(TFT_RED, TFT_BLACK, true);   // regen power, red
    
  spr.drawFloat(fabs(ctr_data.power), 1, spr_width/2, spr.fontHeight()/2);
  
  spr.pushSprite(120 - spr_width / 2, 80);
}


/*********************************************************/

void show_battery() {

  char str[20];
  
  // battery status indicator
  // 84V is low limit
  // 96V is high limit


  // Update the voltage text
  sprintf(str, "%3.1f", ctr_data.voltage);
  vspr.setTextColor(TFT_WHITE, TFT_BLACK, true);
  vspr.drawString(str, vspr_width / 2, vspr.fontHeight()/2);
  vspr.pushSprite(240 - vspr_width, 320 - vspr.fontHeight() + 5);

  
  float low_limit = 84.0;
  float high_limit = 96.0;
  float vtemp = ctr_data.voltage;

  if (vtemp < low_limit)
    vtemp = low_limit;

  if (vtemp > high_limit)
    vtemp = high_limit;


  int steps = 19;
  int width = 7;
  int height = 30;

  float range = high_limit - low_limit;
  int topstep = (ctr_data.voltage - low_limit) / (range / (float) steps);
  
  for (int i=0;i<steps;i++) {
    int n = steps-i;
    int mapmax = steps*steps*steps;

    uint16_t color = rainbow(map(n*n*n, 0, mapmax, 64, 127));
    if (i > topstep) color = 0b0100001000001000;
    tft.fillRoundRect(3 + i*width, 320 - height - 3, width-2, height, 1, color);
  }



}

/*********************************************************/

void show_gear() {
  tft.drawFloat(ctr_data.gear, 0, 220, 15, 4);
}

/*********************************************************/

void show_motor_temp() {
  tft.drawFloat(ctr_data.motor_temp, 0, 150, 135, 4);
}

/*********************************************************/

void show_controller_temp() {
  tft.drawFloat(ctr_data.controller_temp, 0, 150, 160, 4);
}


/*********************************************************/

void show_rpm() {
  // rpm digits
  tft.setTextFont(4);
  int width = tft.textWidth("7777"); 
  tft.setTextPadding(width);
  tft.drawNumber(ctr_data.rpm, 150, 185);

  int w =  (int32_t) (ctr_data.rpm * 218) / 8000; // 0 - 218
  
  // rpm bar
  //tft.drawRect(10, 200, 220, 14, TFT_WHITE);
  tft.fillRoundRect(12, 202, w-1, 10, 0, TFT_CYAN);
  tft.fillRoundRect(12 + w, 202, 218 - w - 1, 10, 0, TFT_BLACK);
}


/*********************************************************/

void show_speed() {
  tft.setTextFont(7);
  int width = tft.textWidth("777"); 
  tft.setTextPadding(width);
  tft.drawFloat(ctr_data.speed, 0, 132, 245);
}




/*********************************************************/

void show_throttle() {
  float t = ctr_data.throttle;
  if (t < 0)
    t = 0;
  if (t > 5000)
    t = 5000;

  uint32_t bar = (uint32_t) (t * 60) / 5000;  // 0 to 60

  // throttle bar
  //tft.drawRect(228, 219, 12, 62, TFT_WHITE);
  tft.fillRoundRect(230, 221 + 60 - bar, 8, bar-1, 0, TFT_MAGENTA);
  tft.fillRoundRect(230, 221, 8, 60-bar-1, 0, TFT_BLACK);
}

/*********************************************************/


// Get coordinates of two ends of a line from r1 to r2, pivot at x,y, angle a
// Coordinates are returned to caller via the xp and yp pointers
#define DEG2RAD 0.0174532925
void getCoord(int16_t x, int16_t y, float *xp1, float *yp1, float *xp2, float *yp2, int16_t r1, int16_t r2, float a)
{
  float sx = cos( (a - 90) * DEG2RAD);
  float sy = sin( (a - 90) * DEG2RAD);
  *xp1 =  sx * r1 + x;
  *yp1 =  sy * r1 + y;
  *xp2 =  sx * r2 + x;
  *yp2 =  sy * r2 + y;
}



/*********************************************************/

// Return a 16 bit rainbow colour
unsigned int rainbow(byte value)
{
  // Value is expected to be in range 0-127
  // The value is converted to a spectrum colour from 0 = blue through to 127 = red

  byte red = 0; // Red is the top 5 bits of a 16 bit colour value
  byte green = 0;// Green is the middle 6 bits
  byte blue = 0; // Blue is the bottom 5 bits

  byte quadrant = value / 32;

  if (quadrant == 0) {
    blue = 31;
    green = 2 * (value % 32);
    red = 0;
  }
  if (quadrant == 1) {
    blue = 31 - (value % 32);
    green = 63;
    red = 0;
  }
  if (quadrant == 2) {
    blue = 0;
    green = 63;
    red = value % 32;
  }
  if (quadrant == 3) {
    blue = 0;
    green = 63 - 2 * (value % 32);
    red = 31;
  }
  return (red << 11) + (green << 5) + blue;
}


/*********************************************************/

void spinner(int x, int y, int active) {
  
  // Draw a segmented spinner
  // Centre of screen
  int cx = x;
  int cy = y;

  // Inner and outer radius of ring
  float r1 = 10.0;
  float r2 = 15.0;

  // Inner and outer line width
  int w1 =  1;
  int w2 =  2;

  // The following will be updated by the getCoord function
  float px1 = 0.0;
  float py1 = 0.0;
  float px2 = 0.0;
  float py2 = 0.0;

  // Wedge line function, an anti-aliased wide line between 2 points, with different
  // line widths at the two ends. Background colour is black.
  for (int angle = 0; angle <= 360; angle += 30) {
    getCoord(cx, cy, &px1, &py1, &px2, &py2, r1, r2, angle);
    uint16_t colour = TFT_BLUE; //rainbow(map(angle, 0, 360, 0, 127));
    if (angle != active) colour = TFT_DARKGREY;
    tft.drawWedgeLine(px1, py1, px2, py2, w1, w2, colour, TFT_BLACK);
  }

}




/*********************************************************/
/*********************************************************/
/*********************************************************/

#if 0
/*
std::string string_to_hex(const std::string& input) {
    static const char hex_digits[] = "0123456789ABCDEF";

    std::string output;
    output.reserve(input.length() * 2);
    for (unsigned char c : input)
    {
        output.push_back(hex_digits[c >> 4]);
        output.push_back(hex_digits[c & 15]);
    }
    return output;
}
*/
#endif

/*********************************************************/


//
// this callback is called everytime a message comes in on the BLE connection
// this happens every 30 ms (but is jittery here, due to various delays and message lengths)
// so the timing between calls are somewhere around 20 to 40 ms
//
void message_handler(uint8_t *pData) {
  uint8_t index;

  int16_t current;
  float rear_wheel_rpm;    // revs per min on rear wheel
  float distance_per_min;  // distance travelled in m/min
  float distance;
  float iq, id, is;

  static uint32_t last_millis = millis();           // time since last msg_0

  uint32_t current_millis = millis();
  uint32_t delta_t = current_millis - last_millis;   // ms since last call 
  last_millis = current_millis;

  //std::string str = string_to_hex(std::string((char*)pData, 16));
  
  pData++;            // skip the 0xAA header
  index = *pData++;   // get address and inc pointer 
  if (index > 29)     // if invalid address
    return;           // skip out

#if ON_SCREEN_MSG_DEBUG
  // save data to message store, skipping the checksum
  memcpy(message_store[index], pData, 12);
#endif

  switch (index) {
    case 0:
      ctr_data.rpm = ((uint16_t) pData[4] << 8) | pData[5];
      
      // calculate speed
      rear_wheel_rpm = (float) ctr_data.rpm / 4.0;                       // revs per min on rear wheel / gearing
      distance_per_min = rear_wheel_rpm * wheel_circumference;  // distance travelled in m/min
      ctr_data.speed = distance_per_min * 0.06;                          // speed in km/h
      
      // calculate distance travelled, since last call
      distance = distance_per_min / 60000.0 * (float) delta_t / 1000.0; // distance in km
    
      ctr_data.gear = ((pData[2] >> 2) & 0x03);  // Gear, 00=high, 11=mid, 10=low, (00=Disabled)
      
      ctr_data.gear -= 1;                        // massage gear into 1=low, 2=mid, 3=high
      if (ctr_data.gear > 2)
        ctr_data.gear = 3;

      iq = (float) (((uint16_t) pData[8] << 8) | pData[9]) / 100.0;     // iq_out in Amps
      id = (float) (((uint16_t) pData[10] << 8) | pData[11]) / 100.0;   // id_out in Amps
      is = sqrt(iq*iq + id*id);                                         // calc vector

      ctr_data.power = - is * ctr_data.voltage / 1000.0;                // power in kW

      if ((iq < 0) || (id < 0))                                         // regen?
        ctr_data.power = -ctr_data.power;

      // update odometer
      odo_total.update_speed(ctr_data.speed);
      odo_trip1.update_speed(ctr_data.speed);
      odo_trip2.update_speed(ctr_data.speed);
      
      // update distance
      odo_total.update_distance(distance);
      odo_trip1.update_distance(distance);
      odo_trip2.update_distance(distance);
    
      // --- Serial output for debugging ---
      Serial.println("\n[FarDriver Data Update]");
      Serial.print("RPM: "); Serial.println(ctr_data.rpm);
      Serial.print("Speed (km/h): "); Serial.println(ctr_data.speed, 2);
      Serial.print("Gear: "); Serial.println(ctr_data.gear);
      Serial.print("Power (kW): "); Serial.println(ctr_data.power, 2);
      break;
    
    case 1:
      ctr_data.voltage = ((uint16_t) pData[0] << 8) | pData[1];    // battery voltage
      ctr_data.voltage /= 10.0;                                     // voltage is given in 100mV steps, convert to float
      
      //current = ((int16_t) pData[6] << 8) | pData[7];     // iQin, negative when driving, positive on regen
      //power = ((float) current/100.0) * voltage / 1000.0;  // power in kW (neg on driving, pos on regen)

      odo_total.update_power(-ctr_data.power);
      odo_trip1.update_power(-ctr_data.power);
      odo_trip2.update_power(-ctr_data.power);
      // --- Serial output for debugging ---
      Serial.print("Voltage (V): "); Serial.println(ctr_data.voltage, 2);
      break;
      
    case 4:
      ctr_data.controller_temp = (float) pData[2];                 // deg C
      // --- Serial output for debugging ---
      Serial.print("Controller Temp (C): "); Serial.println(ctr_data.controller_temp, 1);
      break;
      
    case 13:
      ctr_data.motor_temp = (float) pData[0];                      // deg C
      ctr_data.throttle = ((uint16_t) pData[2] << 8) | pData[3];   // raw ADC reading 0-4095
      // --- Serial output for debugging ---
      Serial.print("Motor Temp (C): "); Serial.println(ctr_data.motor_temp, 1);
      Serial.print("Throttle (raw): "); Serial.println(ctr_data.throttle);
      break;
  }

  
}


/**************************************************************************/
/**************************************************************************/
/**************************************************************************/



#if ON_SCREEN_MSG_DEBUG

int16_t pick_param(int index, int param) {
  uint8_t *pdata = message_store[index];
  return ((int16_t) pdata[param*2] << 8) | pdata[param*2+1];
}

/*********************************************************/

void display_param(int x, int y, int index, int param) {
  char buf[30];
  int16_t p = pick_param(index, param);
  sprintf(buf, "%d, %d : %6d", index, param, p); 
  tft.drawString(buf, x, y);
}

/*********************************************************/

void debug_packets(void) {
    // Plot the label text
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextDatum(ML_DATUM);
  tft.setTextFont(2);
  tft.setTextPadding(tft.textWidth("7777777777777"));
  

  display_param(10, 10, 0, 4);
  display_param(10, 30, 0, 5);
  
  display_param(10, 60, 0, 8);
  display_param(10, 80, 0, 9);
  display_param(10, 100, 0, 10);
  display_param(10, 120, 0, 11);

  display_param(10, 150, 1, 0);
  display_param(10, 170, 1, 1);
  display_param(10, 190, 1, 2);
  display_param(10, 210, 1, 3);
  display_param(10, 230, 1, 4);
  display_param(10, 250, 1, 5);
  display_param(10, 270, 1, 6);
  display_param(10, 290, 1, 7);
  display_param(10, 310, 1, 8);



/*  display_param(10, 80,  2, 0);
  display_param(10, 100, 2, 1);
  display_param(10, 120, 2, 2);
  display_param(10, 140, 2, 3);
  display_param(10, 160, 2, 4);
  display_param(10, 180, 2, 5);

  display_param(10, 210, 3, 0);
  display_param(10, 230, 3, 1);
  display_param(10, 250, 3, 2);
  display_param(10, 270, 3, 3);
  display_param(10, 290, 3, 4);
  display_param(10, 310, 3, 5);

  display_param(130, 80,  1, 0);
  display_param(130, 100, 1, 1);
  display_param(130, 120, 1, 2);
  display_param(130, 140, 1, 3);
  display_param(130, 160, 1, 4);
  display_param(130, 180, 1, 5);
*/
}

#endif


