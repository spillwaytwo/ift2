#! /usr/bin/env python3

import numpy
import imageio.v3 as iio
from PIL import Image, ImageDraw, ImageFont
img = iio.imread('./image.png')
fuel_gauge_pattern = iio.imread("./patterns/fuel-gauge.png")

font_readout = ImageFont.truetype("/usr/share/fonts/TTF/Roboto-Bold.ttf", size = 29, encoding = "unic")

# Map `lo` to `0`, and `hi` to `255`.
def reverselerp(arr, lo, hi):
    return (((arr - lo) / (hi - lo)) * 255).astype('uint8')

def minimax(arr):
    hi = numpy.max(arr, axis = (0, 1))
    lo = numpy.min(arr, axis = (0, 1))

    return reverselerp(arr, lo, hi)

# (x, y): top-left corner of the gauge.
def read_gauge(x, y):
    gauge = img[y:y+13,x:x+250,:]

    gauge = minimax(gauge)

    s = []
    for x in range(0, gauge.shape[1] - 13):
        diff = numpy.sum(numpy.square(gauge[:,x:x+13].astype(float) - fuel_gauge_pattern.astype(float)))
        s.append(diff)

    minimum = min(s)
    idx = s.index(minimum)
    l_off = s[idx - 1] - minimum
    try:
        r_off = s[idx + 1] - minimum
    except:
        r_off = l_off

    return idx + (l_off / (l_off + r_off))

def make_digits(font):
    digits = []

    # Assume `0` is the largest character
    width = font.size * 8 // 12
    height = font.size * 10 // 12
    for i in range(10):
        canvas = Image.new('RGB', [width, height], (0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.text((1, -10), str(i), font = font, fill = "#ffffff")

        digits.append(numpy.asarray(canvas))

    digits.append(numpy.zeros((height, width, 3), dtype = 'uint8'))

    return digits

# (x, y): top-right corner of the text
def read_text(x, y, digits = make_digits(font_readout)):
    x += 4 # roboto font offset! hack.

    num = 0

    for i in range(10):
        digit_scores = []

        drect = [int(x) - digits[0].shape[1], y, digits[0].shape[1], digits[0].shape[0]]
        digit_under_test = img[drect[1]:drect[1]+drect[3], drect[0]:drect[0]+drect[2], :]

        if i == 0:
            lo = numpy.min(digit_under_test, axis = (0, 1))
            hi = numpy.max(digit_under_test, axis = (0, 1))

        digit_under_test = reverselerp(digit_under_test, lo, hi)
        
        for digit in digits:
            score = numpy.sum(numpy.square(digit_under_test.astype(float) - digit.astype(float)))
            digit_scores.append(score)

        x -= drect[2] - 3

        minimum = min(digit_scores)
        min_idx = digit_scores.index(minimum)
        if min_idx == 10 or minimum > 40_000_000.0: break
        num += min_idx * (10 ** i)

    return num

print("TIME, BLOX, BCH4, BVEL, BALT, BENG, SLOX, SCH4, SVEL, SALT, SENG")

import numpy as np
import math

booster_engines_center = np.array([109, 982])
ship_engines_center = np.array([1815, 995])

def ring(center, radius, count, start_rot):
    for i in range(count):
        angle = start_rot + (360 / count) * i
        angle = math.radians(angle)

        offset = np.array([math.sin(angle), -math.cos(angle)])
        yield center + offset * radius

# Engine numbers are accurate, as far as I know.
# Engines are numbered clockwise from below.
# On the webcast, E1 is pointing 120 degrees clockwise from up, and viewed from below.
booster_engine_coords = [
    *ring(booster_engines_center, 13, 3, 120),
    *ring(booster_engines_center, 36, 10, 120),
    *ring(booster_engines_center, 62, 20, 120 + 9),
]

# Probably not accurate.
# One vacuum engine is by the heat shielding, pointing away-from-tower.
# Assuming that the order of the center engines is the same at the booster, E1 points towards the tower, and the tower is between E4 and E6. (No numbers are known, but I'm assuming center are E1-E3 and vacuum are E4-E6)
# On the webcast, I'm assuming E1 points 60 degrees *counter-clockwise* from up. The hotstaging on IFT-2 (top engine on webcast is a little late, but the plume behind the booster seems a little delayed; would correspond to the angle between E1 and E3) seems to support this, but it's not very clear.
ship_engine_coords = [
    *ring(ship_engines_center, 17, 3, 180 + 120),
    *ring(ship_engines_center, 58, 3, 180 + 120 + 60),
]

prev = ""

with iio.imopen("video.mp4", "r", plugin = "pyav") as img_file:
    # frame 69705: T-10
    # frame 85255: after ship telemetry loss
    time = -11
    for frame in range(69705, 85255):
        time += 1/30
        img = img_file.read(index = frame)

        booster_lox = read_gauge(274, 1000)
        booster_ch4 = read_gauge(274, 1035)

        ship_lox = read_gauge(1455, 1000)
        ship_ch4 = read_gauge(1455, 1035)

        booster_vel = read_text(438, 915)
        booster_alt = read_text(438, 949)

        ship_vel = read_text(1619, 915)
        ship_alt = read_text(1619, 949)

        engines = []

        for coord in [*booster_engine_coords, *ship_engine_coords]:
            px = img[int(coord[1])][int(coord[0])].astype('float')
            mid = (px[0] + px[1] + px[2]) / 3
            rel = (px[0] - mid) + (px[1] - mid) + (px[2] - mid)
            engines.append(px[0] > 80 and px[1] > 80 and px[2] > 80 and rel < 15)

        booster_engine_bits = sum([1<<i if on else 0 for i, on in enumerate(engines[0:len(booster_engine_coords)])])
        ship_engine_bits = sum([1<<i if on else 0 for i, on in enumerate(engines[len(booster_engine_coords):])])
        
        print(f"{time:.3f}, {booster_lox:.2f}, {booster_ch4:.2f}, {booster_vel}, {booster_alt}, {booster_engine_bits}, {ship_lox:.2f}, {ship_ch4:.2f}, {ship_vel}, {ship_alt}, {ship_engine_bits}")
            
