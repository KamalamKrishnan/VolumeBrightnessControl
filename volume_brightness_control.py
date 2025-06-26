import cv2
import numpy as np
import math
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
import screen_brightness_control as sbc
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import HandTrackingModule as htm  # Make sure this is in your folder

# Setup webcam
wCam, hCam = 640, 480
cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)

# Hand detector
detector = htm.handDetector(detectionCon=0.7)

# Audio setup
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
vol_min, vol_max = volume_ctrl.GetVolumeRange()[:2]

# Initial values
mode = "volume"
vol_bar = 400
bright_bar = 400
vol_percentage = 0
bright_percentage = 0
is_muted = False
mute_gesture_prev = False

while True:
    success, img = cap.read()
    img = detector.findHands(img)
    lmList = detector.findPosition(img, draw=False)

    if len(lmList) != 0:
        x1, y1 = lmList[4][1], lmList[4][2]   # Thumb
        x2, y2 = lmList[8][1], lmList[8][2]   # Index
        cx, cy = (x1 + x2)//2, (y1 + y2)//2
        length = math.hypot(x2 - x1, y2 - y1)

        fingers = detector.fingersUp()

        # Detect mute toggle: Only pinky up
        if fingers == [0, 0, 0, 0, 1]:
            if not mute_gesture_prev:
                is_muted = not is_muted
                volume_ctrl.SetMute(is_muted, None)
            mute_gesture_prev = True
        else:
            mute_gesture_prev = False

        # Switch to volume mode: index + middle finger
        if fingers == [0, 1, 1, 0, 0]:
            mode = "volume"
            if is_muted:
                is_muted = False
                volume_ctrl.SetMute(False, None)

        # Switch to brightness mode: all fingers up
        elif fingers == [1, 1, 1, 1, 1]:
            mode = "brightness"

        # Adjust based on mode and mute status
        if not is_muted:
            if mode == "volume":
                vol = np.interp(length, [20, 150], [vol_min, vol_max])
                vol_percentage = np.interp(length, [20, 150], [0, 100])
                vol_bar = np.interp(length, [20, 150], [400, 150])
                volume_ctrl.SetMasterVolumeLevel(vol, None)

            elif mode == "brightness":
                bright_percentage = int(np.interp(length, [20, 150], [0, 100]))
                bright_bar = np.interp(length, [20, 150], [400, 150])
                sbc.set_brightness(bright_percentage)

        else:
            # If muted, override volume display
            vol_percentage = 0
            vol_bar = 400

        # Drawing hand landmarks
        color = (0, 255, 0) if mode == "volume" else (255, 255, 0)
        cv2.circle(img, (x1, y1), 10, color, cv2.FILLED)
        cv2.circle(img, (x2, y2), 10, color, cv2.FILLED)
        cv2.line(img, (x1, y1), (x2, y2), color, 3)
        cv2.circle(img, (cx, cy), 10, color, cv2.FILLED)

    # Volume Bar UI
    cv2.rectangle(img, (50, 150), (85, 400), (50, 50, 50), 3)
    cv2.rectangle(img, (50, int(vol_bar)), (85, 400), (0, 255, 0), cv2.FILLED)
    cv2.putText(img, f'Vol: {int(vol_percentage)}%', (35, 440),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Brightness Bar UI
    cv2.rectangle(img, (560, 150), (595, 400), (50, 50, 50), 3)
    cv2.rectangle(img, (560, int(bright_bar)),
                  (595, 400), (255, 255, 0), cv2.FILLED)
    cv2.putText(img, f'Bright: {int(bright_percentage)}%', (460, 440),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    # Display Current Mode
    mode_color = (0, 255, 255) if mode == "volume" else (255, 255, 0)
    cv2.putText(img, f'MODE: {mode.upper()}', (220, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, mode_color, 3)

    # Show mute text if muted
    if is_muted:
        cv2.putText(img, 'MUTED', (250, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

    # Show window
    cv2.imshow("Gesture Volume & Brightness Controller", img)

    # Exit when 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
