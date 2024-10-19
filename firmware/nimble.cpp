



#include "nimble.h"

#include <NimBLEDevice.h>

volatile bool is_connected = false;
volatile bool service_found = true;

static uint32_t scanTime = 0; /** 0 = scan forever */


void scanEndedCB(NimBLEScanResults results);

static NimBLEAdvertisedDevice* advDevice;


extern void message_handler(uint8_t *pData);

/*********************************************************/

/**  None of these are required as they will be handled by the library with defaults. **
 **                       Remove as you see fit for your needs                        */
class ClientCallbacks : public NimBLEClientCallbacks {
    void onConnect(NimBLEClient* pClient) {
//        Serial.println("Connected");
        /** After connection we should change the parameters if we don't need fast response times.
         *  These settings are 150ms interval, 0 latency, 450ms timout.
         *  Timeout should be a multiple of the interval, minimum is 100ms.
         *  I find a multiple of 3-5 * the interval works best for quick response/reconnect.
         *  Min interval: 120 * 1.25ms = 150, Max interval: 120 * 1.25ms = 150, 0 latency, 60 * 10ms = 600ms timeout
         */

        pClient->updateConnParams(6, 16, 0, 100);
    };

    void onDisconnect(NimBLEClient* pClient) {
        Serial.print(pClient->getPeerAddress().toString().c_str());
        Serial.println(" Disconnected - Starting scan");
        is_connected = false;
//        NimBLEDevice::getScan()->start(scanTime, scanEndedCB);
    };


    /** Called when the peripheral requests a change to the connection parameters.
     *  Return true to accept and apply them or false to reject and keep
     *  the currently used parameters. Default will return true.
     */
    bool onConnParamsUpdateRequest(NimBLEClient* pClient, const ble_gap_upd_params* params) {

//        Serial.println("** onConnParamsUpdateRequest");
//        Serial.println(params->itvl_min);
//        Serial.println(params->itvl_max);
//        Serial.println(params->latency);
//        Serial.println(params->supervision_timeout);
#if 0
        if(params->itvl_min < 24) { /** 1.25ms units */
            return false;
        } else if(params->itvl_max > 40) { /** 1.25ms units */
            return false;
        } else if(params->latency > 2) { /** Number of intervals allowed to skip */
            return false;
        } else if(params->supervision_timeout > 100) { /** 10ms units */
            return false;
        }
#endif
        return true;
    };

};



/*********************************************************/

/** Define a class to handle the callbacks when advertisments are received */
class AdvertisedDeviceCallbacks: public NimBLEAdvertisedDeviceCallbacks {

    void onResult(NimBLEAdvertisedDevice* advertisedDevice) {
//        Serial.print("Advertised Device found: ");
//        Serial.println(advertisedDevice->toString().c_str());
        if(advertisedDevice->isAdvertisingService(NimBLEUUID("FFE0"))) {
            Serial.println("Found Our Service");
            /** stop scan before connecting */
            NimBLEDevice::getScan()->stop();
            /** Save the device reference in a global for the client to use*/
            advDevice = advertisedDevice;
            /** Ready to connect now */
            service_found = true;
        }
    };
};


/*********************************************************/

/** Notification / Indication receiving handler callback */
void notifyCB(NimBLERemoteCharacteristic* pRemoteCharacteristic, uint8_t* pData, size_t length, bool isNotify) {
  if (length == 16) {
    message_handler(pData);
  }
}




/*********************************************************/

/** Callback to process the results of the last scan or restart it */
void scanEndedCB(NimBLEScanResults results) {
//    Serial.println("Scan Ended");
}


/** Create a single global instance of the callback class to be used by all clients */
static ClientCallbacks clientCB;

static NimBLERemoteService* pSvc = nullptr;
static NimBLERemoteCharacteristic* pRemChar = nullptr;
static NimBLERemoteDescriptor* pDsc = nullptr;


/*********************************************************/

/** Handles the provisioning of clients and connects / interfaces with the server */
bool connectToServer() {
    NimBLEClient* pClient = nullptr;

    /** Check if we have a client we should reuse first **/
    if(NimBLEDevice::getClientListSize()) {
        /** Special case when we already know this device, we send false as the
         *  second argument in connect() to prevent refreshing the service database.
         *  This saves considerable time and power.
         */
        pClient = NimBLEDevice::getClientByPeerAddress(advDevice->getAddress());
        if(pClient){
            if(!pClient->connect(advDevice, false)) {
                Serial.println("Reconnect failed");
                return false;
            }
            Serial.println("Reconnected client");
        }
        /** We don't already have a client that knows this device,
         *  we will check for a client that is disconnected that we can use.
         */
        else {
            pClient = NimBLEDevice::getDisconnectedClient();
        }
    }

    /** No client to reuse? Create a new one. */
    if (!pClient) {

        if(NimBLEDevice::getClientListSize() >= NIMBLE_MAX_CONNECTIONS) {
            Serial.println("Max clients reached - no more connections available");
            return false;
        }

        pClient = NimBLEDevice::createClient();
//        Serial.println("New client created");

        pClient->setClientCallbacks(&clientCB, false);

        /** Set initial connection parameters: These settings are 15ms interval, 0 latency, 120ms timout.
         *  These settings are safe for 3 clients to connect reliably, can go faster if you have less
         *  connections. Timeout should be a multiple of the interval, minimum is 100ms.
         *  Min interval: 12 * 1.25ms = 15, Max interval: 12 * 1.25ms = 15, 0 latency, 51 * 10ms = 510ms timeout
         */
        pClient->setConnectionParams(6, 16, 0, 100);


        /** Set how long we are willing to wait for the connection to complete (seconds), default is 30. */
        pClient->setConnectTimeout(30);


        if (!pClient->connect(advDevice)) {
            /** Created a client but failed to connect, don't need to keep it as it has no data */
            NimBLEDevice::deleteClient(pClient);
            Serial.println("Failed to connect, deleted client");
            return false;
        }
    }


    if(!pClient->isConnected()) {
        if (!pClient->connect(advDevice)) {
            Serial.println("Failed to connect");
            return false;
        }
    }


    Serial.print("Connected to: ");
    Serial.println(pClient->getPeerAddress().toString().c_str());
    Serial.print("RSSI: ");
    Serial.println(pClient->getRssi());


    /** Now we can read/write/subscribe the characteristics of the services we are interested in */

    pSvc = pClient->getService("FFE0");
    if(pSvc)     /** make sure it's not null */
        pRemChar = pSvc->getCharacteristic("FFEC");

    if(pRemChar) {     /** make sure it's not null */

        if(pRemChar->canWrite())
          Serial.println("Can Write");

        /** registerForNotify() has been deprecated and replaced with subscribe() / unsubscribe().
         *  Subscribe parameter defaults are: notifications=true, notifyCallback=nullptr, response=false.
         *  Unsubscribe parameter defaults are: response=false.
         */
        if(pRemChar->canNotify()) {
            if(!pRemChar->subscribe(true, notifyCB)) {
                /** Disconnect if subscribe failed */
                pClient->disconnect();
                return false;
            }
//            Serial.println("Subscribed, NOTIFY.");
        }
        else if(pRemChar->canIndicate()) {
            /** Send false as first argument to subscribe to indications instead of notifications */
            if(!pRemChar->subscribe(false, notifyCB)) {
                /** Disconnect if subscribe failed */
                pClient->disconnect();
                return false;
            }
//          Serial.println("Subscribed, INDICATE.");
        }

    }
    else
        Serial.println("Service not found.");

    //Serial.println("Done with this device!");

    return true;
}





void nimble_start(void) {

  service_found = false;

  /** Initialize NimBLE, no device name spcified as we are not advertising */
  NimBLEDevice::init("");

  /** Optional: set the transmit power, default is 3db */
  NimBLEDevice::setPower(ESP_PWR_LVL_P9); /** +9db */

  /** create new scan */
  NimBLEScan* pScan = NimBLEDevice::getScan();

  /** create a callback that gets called when advertisers are found */
  pScan->setAdvertisedDeviceCallbacks(new AdvertisedDeviceCallbacks());

  /** Set scan interval (how often) and window (how long) in milliseconds */
  pScan->setInterval(45);
  pScan->setWindow(15);

  /** Active scan will gather scan response data from advertisers
   *  but will use more energy from both devices
   */
  pScan->setActiveScan(true);

  /** Start scanning for advertisers for the scan time specified (in seconds) 0 = forever
   *  Optional callback for when scanning stops.
   */
  pScan->start(scanTime, scanEndedCB);

}

bool nimble_send(uint8_t *pData, uint16_t len) {
  return pRemChar->writeValue(pData, len, false);
}
