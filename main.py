import numpy as nm
import cv2
import pytesseract
import time
import math
from PIL import ImageGrab, ImageFilter
import pygame
import pygame_gui
from datetime import datetime
import re
import tkinter as tk
from tkinter import simpledialog
import threading
import pydirectinput
import tempfile
import gtts
import os

pytesseract.pytesseract.tesseract_cmd = 'C:/Users/' + os.environ.get('USERNAME') + '/AppData/Local/Programs/Tesseract-OCR/tesseract.exe'

ATOactive = False
TTSactive = False
solve = None
continuing = False
ignorelim = False
ignoreaws = False

spd_pos = (884, 957, 947, 985)
lim_pos = (889, 987, 942, 1016)
green_pos = (1440, 983, 1441, 984)
yellow_pos = (1438, 1016, 1439, 1017)
double_yellow_pos = (1438, 950, 1439, 951)
red_pos = (1438, 1045, 1439, 1046)
distance_pos = (555, 1046, 605, 1070)
awsbutton_pos = (1330, 994, 1331, 995)
throttle_pos = (843, 931, 845, 1074)
doors_pos = (870, 822, 871, 823)
loading_pos = (781, 823, 782, 824)
continue_pos = (1032, 460, 1033, 461)
undershoot_pos = (709, 906, 710, 907)
awaiting_pos = (862, 823, 863, 824)
buzzer_pos = (824, 816, 825, 817)

pygame.init()
pygame.mixer.init()

window_surface = pygame.display.set_mode((400, 100), pygame.DOUBLEBUF)
pygame.display.set_caption("ATOmatic - v1.0 Pre-Release")

icon = pygame.image.load('images/icon.png')
pygame.display.set_icon(icon)

background = pygame.Surface((400, 100))
background.fill(pygame.Color('#1f1f1f'))

manager = pygame_gui.UIManager((400, 100))
clock = pygame.time.Clock()
is_running = True

lblMaxSpeed = pygame_gui.elements.UILabel(
    relative_rect=pygame.Rect((10, 10), (250, 30)), 
    text='Automatic Train Operator for SCR', 
    manager=manager,
    object_id="#title"
)
lblTime = pygame_gui.elements.UILabel(
    relative_rect=pygame.Rect((270, 10), (100, 30)), 
    text='', 
    manager=manager,
    object_id="#time"
)
toggleATO_btn = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((10, 50), (120, 40)), 
    text='ATO Toggle', 
    manager=manager,
    object_id="#toggleATO"
)
setMaxSpeed_btn = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((140, 50), (120, 40)), 
    text='Set Max Speed', 
    manager=manager,
    object_id="#setMaxSpeed"
)
toggleTTS = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((270, 50), (120, 40)), 
    text='Toggle TTS', 
    manager=manager,
    object_id="#toggleTTS"
)

def changeColour(button, selColour):
    button.colours['normal_bg'] = pygame.Color(selColour)
    button.rebuild()

def create_dialog(title, question):
    root = tk.Tk()
    root.withdraw()
    userInput = simpledialog.askstring(title, question)
    root.destroy()
    return userInput

def forInputClick():
    threading.Thread(target=create_dialog, daemon=True).start()

def TTSNS():
    if TTSactive:
        tts = gtts.gTTS("Station Reached. Train Stopping")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            tts.save(temp_file.name)
            temp_filename = temp_file.name
        pygame.mixer.music.load(temp_filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
        os.remove(temp_filename)

def TTSRED():
    if TTSactive:
        tts = gtts.gTTS("ATO DISENGAGED. DANGER ASPECT AHEAD. TAKE MANUAL CONTROL")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            tts.save(temp_file.name)
            temp_filename = temp_file.name
        pygame.mixer.music.load(temp_filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
        os.remove(temp_filename)

def throttle(fromThrottle, toThrottle):
    throttleDiff = toThrottle - fromThrottle

    if toThrottle == 0:
        throttleDiff -= 5

    if throttleDiff > 0:
        key = "w"
    elif throttleDiff < -1:
        key = "s"
    else:
        return

    print("Throttle: ", throttleDiff)
    pressTime = abs((throttleDiff / 5) * 0.10)

    if -4 < throttleDiff < 0:
        pydirectinput.keyDown(key)
        pydirectinput.keyUp(key)
    else: 
        pydirectinput.keyDown(key)
        time.sleep(pressTime)
        pydirectinput.keyUp(key)
    return

def task():
    curLim = 0
    global ATOactive
    global TTSactive
    global solve
    global continuing
    global ignorelim
    global ignoreaws

    while ATOactive:
        im = ImageGrab.grab(bbox=(awsbutton_pos))
        pix = im.load()
        awsbutton_value = pix[0, 0]
        if awsbutton_value == (255, 255, 255):
            pydirectinput.keyDown("q")
            pydirectinput.keyUp("q")
            print("Reset the AWS")
        
        cap = ImageGrab.grab(bbox=(throttle_pos))
        img = cap
        count = 0
        bottom_throttle_pixel = None
        for y in range(img.height):
            for x in range(img.width):
                pixel = img.getpixel((x, y))
                if y == img.height - 1:
                    bottom_throttle_pixel = pixel
                if pixel == (0, 176, 85):
                    count += 1

        currentThrottle = int(math.floor(100 * (count / 142)))

        print("Current throttle: ", currentThrottle)

        cap = ImageGrab.grab(bbox=(lim_pos))
        cap = cap.filter(ImageFilter.MedianFilter())
        cap = cv2.cvtColor(nm.array(cap), cv2.COLOR_RGB2GRAY)
        tesstr = pytesseract.image_to_string(cap, config="--psm 7")
        compareLim = [int(s) for s in re.findall(r'\b\d+\b', tesstr)]
        if compareLim and curLim != compareLim[0]:
            pygame.mixer.Sound('sounds/change.wav').play()
        
        lim = 0
        lim = [int(s) for s in re.findall(r'\b\d+\b', tesstr)]
        if lim:
            curLim = int(lim[0])
        
        cap = ImageGrab.grab()
        src = nm.array(cap)
        gray = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY)
        gray = cv2.medianBlur(gray, 5)
        rows = gray.shape[0]
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, rows / 8, param1=100, param2=30, minRadius=1, maxRadius=30)
                
        if circles is not None:
            circles = nm.uint16(nm.around(circles))
            for i in circles[0, :]:
                x = i[0] - i[2]
                y = i[1] - i[2]
                w = 2 * i[2]
                h = 2 * i[2]
                center = (i[0], i[1])
                if w > 39:
                    txt = pytesseract.image_to_string(gray[y:y + h, x:x + w], config="--psm 6")
                    if "W" in txt:
                        pydirectinput.keyDown("h")
                        pydirectinput.keyUp("h")
                cv2.circle(src, center, 1, (0, 100, 100), 3)
                radius = i[2]
                cv2.circle(src, center, radius, (255, 0, 255), 3)

        templim = lim[0] if lim else 0
        lim = templim
        if not ignoreaws:
            im = ImageGrab.grab(bbox=(red_pos))
            pix = im.load()
            red_value = pix[0, 0]
            im = ImageGrab.grab(bbox=(yellow_pos))
            pix = im.load()
            yellow_value = pix[0, 0]
            im = ImageGrab.grab(bbox=(green_pos))
            pix = im.load()
            green_value = pix[0, 0]
            im = ImageGrab.grab(bbox=(double_yellow_pos))
            pix = im.load()
            double_yellow_value = pix[0, 0]
            if red_value == (255, 0, 0):
                print("AWS:", "red")
                lim = 0
                ATOactive = False
                changeColour(toggleATO_btn, '#FF0000')
                pygame.mixer.Sound('sounds/ATORedStop.wav').play()
                threading.Thread(target=TTSRED, daemon=True).start()
            if yellow_value == (255, 190, 0):
                print("AWS:", "yellow")
                if templim > 45:
                    lim = 45
            if double_yellow_value == (255, 190, 0):
                print("AWS:", "double_yellow")
                if templim > 75:
                    lim = 75
            if green_value == (0, 255, 0):
                print("AWS:", "green")

        print("Limit: ", lim)
        limitThrottle = int((lim / max_speed) * 100)

        print("Limit throttle: ", limitThrottle)

        cap = ImageGrab.grab(bbox=(distance_pos))
        cap = cap.filter(ImageFilter.MedianFilter())
        cap = cv2.cvtColor(nm.array(cap), cv2.COLOR_RGB2GRAY)
        tesstr = pytesseract.image_to_string(cap, config="--psm 6")
        distance = [int(s) for s in re.findall(r'\b\d+\b', tesstr)]
        try:
            m_distance = distance[0]
            distance = distance[1]
            print(m_distance, distance)
            if distance == 0 and m_distance == 0 or continuing:
                im = ImageGrab.grab(bbox=(loading_pos))
                pix = im.load()
                loading_value = pix[0, 0]
                im = ImageGrab.grab(bbox=(doors_pos))
                pix = im.load()
                doors_value = pix[0, 0]
                im = ImageGrab.grab(bbox=(undershoot_pos))
                pix = im.load()
                undershoot_value = pix[0, 0]
                im = ImageGrab.grab(bbox=(awaiting_pos))
                pix = im.load()
                awaiting_value = pix[0, 0]
                im = ImageGrab.grab(bbox=(buzzer_pos))
                pix = im.load()
                buzzer_value = pix[0, 0]
                print(buzzer_value)
                if undershoot_value == (255, 255, 255):
                    print("UNDERSHOOT")
                    pydirectinput.keyDown("w")
                    time.sleep(0.4)
                    pydirectinput.keyUp("w")
                if doors_value == (255, 255, 255):
                    print("CLOSING DOORS")
                    pydirectinput.keyDown("t")
                    pydirectinput.keyUp("t")
                    time.sleep(4)
                    continuing = False
                    ignorelim = False
                    ignoreaws = False
                elif loading_value == (255, 255, 255):
                    print("LOADING")
                elif awaiting_value == (255, 255, 255):
                    print("WAITING FOR GUARD")
                elif buzzer_value == (255, 255, 255):
                    print("ACTIVATING THE BUZZER")
                    pydirectinput.keyDown("t")
                    pydirectinput.keyUp("t")
                else:
                    print("ATO Stopping")
                    pygame.mixer.Sound('sounds/change.wav').play()
                    threading.Thread(target=TTSNS, daemon=True).start()
                    pydirectinput.keyDown("s")
                    pydirectinput.keyUp("s")
                    time.sleep(3)
                    pydirectinput.keyDown("s")
                    time.sleep(5)
                    pydirectinput.keyUp("s")
                    pydirectinput.keyDown("t")
                    pydirectinput.keyUp("t")
            elif distance <= 20 and m_distance == 0:
                if lim >= 45:
                    print("Slowing down to prepare for station arrival.")
                    ignoreaws = True
                    ignorelim = True
                    throttle(currentThrottle, int((42 / max_speed) * 100))
                else:
                    throttle(currentThrottle, limitThrottle)
            else:
                throttle(currentThrottle, limitThrottle)
        except IndexError:
            pass

def runATO():
    threading.Thread(target=task, daemon=True).start()

while is_running:
    time_delta = clock.tick(60) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            is_running = False

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == toggleATO_btn:
                if not ATOactive:   
                    ATOactive = True
                    changeColour(toggleATO_btn, '#006600')
                    threading.Thread(target=runATO, daemon=True).start()
                else:
                    ATOactive = False
                    changeColour(toggleATO_btn, '#660000')
            if event.ui_element == setMaxSpeed_btn:
                max_speed = int(create_dialog("ATOmatic - Data Entry", "Enter the Train's maximum speed"))
            if event.ui_element == toggleTTS:
                if not TTSactive:
                    TTSactive = True
                    changeColour(toggleTTS, '#006600')
                else:
                    TTSactive = False
                    changeColour(toggleTTS, '#660000')

        curTime = datetime.now().strftime("%H:%M:%S")
        lblTime.set_text(curTime)

        manager.process_events(event)
        manager.update(time_delta)

    window_surface.blit(background, (0, 0))
    manager.draw_ui(window_surface)

    pygame.display.update()
