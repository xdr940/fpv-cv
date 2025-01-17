import usb.core
import usb.util
import threading
import time

# The DJI Headset should be VID 0x2ca3 and PID 0x1f
VID=0x2ca3
PID=0x1f

# Command verb to make the dump available:
MagicPacket = "524d5654"

# For the bulk transfer handle, we want interface 3:
"""
    INTERFACE 3: Vendor Specific ===========================
     bLength            :    0x9 (9 bytes)
     bDescriptorType    :    0x4 Interface
     bInterfaceNumber   :    0x3
     bAlternateSetting  :    0x0
     bNumEndpoints      :    0x2
     bInterfaceClass    :   0xff Vendor Specific
     bInterfaceSubClass :   0x43
     bInterfaceProtocol :    0x1
     iInterface         :    0xb BULK Interface
      ENDPOINT 0x3: Bulk OUT ===============================
       bLength          :    0x7 (7 bytes)
       bDescriptorType  :    0x5 Endpoint
       bEndpointAddress :    0x3 OUT
       bmAttributes     :    0x2 Bulk
       wMaxPacketSize   :  0x200 (512 bytes)
       bInterval        :    0x0
      ENDPOINT 0x84: Bulk IN ===============================
       bLength          :    0x7 (7 bytes)
       bDescriptorType  :    0x5 Endpoint
       bEndpointAddress :   0x84 IN
       bmAttributes     :    0x2 Bulk
       wMaxPacketSize   :  0x200 (512 bytes)
       bInterval        :    0x0

"""


class USBDev:
    def __init__(self):
        self.HasStream = False
        self.DevicePresent = False       
        self.DeviceHandle = None
        self.ManuallyClaimed = False
        self.CheckThreadRunning = False
        self.ReadThreadRunning = False
        self.LastError = None
        self.DeviceStatus = None#public

    def _pollDev(self):
        dev = usb.core.find(idVendor=VID, idProduct=PID)
        if dev is None:
            self.DevicePresent = False#public
            self.DeviceHandle = None
            self.DeviceCfg = None
            self.DeviceInterface = None
            self.InPoint = None
            self.OutPoint = None
            self.DeviceStatus = None
        else:
            self.DevicePresent = True
            self.DeviceHandle = dev
            self.DeviceCfg = dev[0]
            self.DeviceInterface = self.DeviceCfg[(3,0)]
            # The inpoint and outpoint maybe could be enumerated via usb.util.endpoint_direction if needed:
            self.InPoint = self.DeviceInterface[1]
            self.OutPoint = self.DeviceInterface[0]

    def _claimDev(self):
        if self.DevicePresent:
            usb.util.claim_interface(self.DeviceHandle, self.DeviceInterface)
            self.ManuallyClaimed = True

    def _releaseDev(self):
        if self.ManuallyClaimed and self.DevicePresent:
            usb.util.release_interface(self.DeviceHandle, self.DeviceInterface)
            self.ManuallyClaimed = False

    def _sendData(self, Data: bytearray):
        if not self.DeviceHandle:
            return None
        try: 
            rv = self.DeviceHandle.write(self.OutPoint.bEndpointAddress, Data, timeout=500)
        except usb.core.USBError as er:
            # print("DEBUG: Error in _sendData(): {}".format(er.strerror))
            # self.CheckThreadRunning = False
            self.LastError = er
            return None
        print("DEBUG: Wrote " + str(rv) + " bytes to outpoint")
        return rv
    
    def _sendMagicPacket(self):
        magic = bytearray.fromhex(MagicPacket)
        self.DeviceStatus = "Sending Magic Packet"
        # Try a few times to send the magic packet
        # Headset initialization takes time, first attempt might time out
        for x in range(5):       
            bs = self._sendData(magic)
            if bs == None:
                # Need to retry, so we give it a 500ms pause to limit USB queries:
                time.sleep(.5)
                continue
            else:
                # Successful send
                self.MagicPacketSent = True
                self.DeviceStatus = "Magic Packet Sent"
                return bs



    def _devPollLoop(self):
        self.CheckThreadRunning = True
        while True:
            print("DEBUG: Device poll loop is running...")
            PriorState = self.DevicePresent
            self._pollDev()
            if self.DevicePresent != PriorState:
                print("DEBUG: Device State changed, new state is " + str(self.DevicePresent))
                # Adjust the state to the magic packet not having been sent, so a re-init is done
                self.MagicPacketSent = False
                # We need to shut down the headset scanner thread because of USB contention:
                self.CheckThreadRunning = False
            # Need to validate this works:
            if self.CheckThreadRunning == False:
                print("DEBUG: Shutting down device poll loop...")
                return
            time.sleep(.5)

    #public
    def startDevCheckThread(self):
        if self.CheckThreadRunning:
            return
        devCheckThreadHandle = threading.Thread(target=self._devPollLoop)
        devCheckThreadHandle.start()
        # public

    def RecvData(self):
        if not self.DeviceHandle:
            return None
        if not self.MagicPacketSent:
            sb = self._sendMagicPacket()
            if not self.MagicPacketSent:
                # It is still not sent, so don't bother trying to read
                return None
        try:
            rv = self.DeviceHandle.read(self.InPoint.bEndpointAddress, self.InPoint.wMaxPacketSize)
        except usb.core.USBError as er:
            # print("DEBUG: Error in RecvData(): {}".format(er.strerror))
            self.LastError = er
            # If the error is "No such device, revert back to device detection"
            # TODO: Code based?  probably won't work on non en-US
            if "No such device" in er.strerror:  # and not self.CheckThreadRunning:
                self.DevicePresent = False
                # And we need to give the first iteration of the detect loop time to finish:
                time.sleep(2)
                self.startDevCheckThread()
                return None

            else:
                # self.startDevCheckThread()#试试这个能好吗


                # This is probably a timeout, just waiting for a stream to start:
                print(er)

                if "No such device" in er.strerror:
                    self.DeviceStatus = "No such device, Waiting for Stream"
                if not self.CheckThreadRunning:
                    self.DeviceStatus = "CheckThreadRunning false, Waiting for Stream"
                return None

        # print("DEBUG: Read " + str(len(rv)) + " bytes from goggles")
        # Successful read if we get here
        self.DeviceStatus = "Streaming Data"
        return rv