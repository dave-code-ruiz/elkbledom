from enum import Enum

DOMAIN = "elkbledom"
CONF_RESET = "reset"
CONF_DELAY = "delay"

# Brightness mode configuration
CONF_BRIGHTNESS_MODE = "brightness_mode"
BRIGHTNESS_MODES = ["auto", "rgb", "native"]
DEFAULT_BRIGHTNESS_MODE = "auto"

class EFFECTS (Enum):
    # Light Effects (0x87-0x9C)
    jump_red_green_blue = 0x87
    jump_red_green_blue_yellow_cyan_magenta_white = 0x88
    crossfade_red = 0x8b
    crossfade_green = 0x8c
    crossfade_blue = 0x8d
    crossfade_yellow = 0x8e
    crossfade_cyan = 0x8f
    crossfade_magenta = 0x90
    crossfade_white = 0x91
    crossfade_red_green = 0x92
    crossfade_red_blue = 0x93
    crossfade_green_blue = 0x94
    crossfade_red_green_blue = 0x89
    crossfade_red_green_blue_yellow_cyan_magenta_white = 0x8a
    blink_red = 0x96
    blink_green = 0x97
    blink_blue = 0x98
    blink_yellow = 0x99
    blink_cyan = 0x9a
    blink_magenta = 0x9b
    blink_white = 0x9c
    blink_red_green_blue_yellow_cyan_magenta_white = 0x95

class EFFECTS_MELK (Enum):
    Switches_All_Omni = 0x00
    Soft_Fade_All_R = 0x01
    Chase_W_CI = 0x4b
    Chase_All_CO = 0x3a
    Chase_All_SL = 0x4d
    Fade_G_R = 0x1c
    Chase_RWR_L = 0x9b
    Chase_WBW_L = 0x97
    Chase_RWR_R = 0x9c
    Chase_WBW_R = 0x98
    Fast_Chase_All_R = 0x10
    Fade_C_L = 0x21
    Fade_RGB_L = 0x05
    Fade_All_R = 0x16
    Fade_R_R = 0x1a
    Chase_All_R = 0x0a

EFFECTS_list = ['jump_red_green_blue',
    'jump_red_green_blue_yellow_cyan_magenta_white',
    'crossfade_red',
    'crossfade_green',
    'crossfade_blue',
    'crossfade_yellow',
    'crossfade_cyan',
    'crossfade_magenta',
    'crossfade_white',
    'crossfade_red_green',
    'crossfade_red_blue',
    'crossfade_green_blue',
    'crossfade_red_green_blue',
    'crossfade_red_green_blue_yellow_cyan_magenta_white',
    'blink_red',
    'blink_green',
    'blink_blue',
    'blink_yellow',
    'blink_cyan',
    'blink_magenta',
    'blink_white',
    'blink_red_green_blue_yellow_cyan_magenta_white'
    ]

EFFECTS_list_MELK = ['Switches_All_Omni',
    'Soft_Fade_All_Red',
    'Chase_W_CI',
    'Chase_All_CO',
    'Chase_All_SL',
    'Fade_Green_Right',
    'Chase_Red_White_Red_Left',
    'Chase_White_Blue_White_Left',
    'Chase_Red_White_Red_Right',
    'Chase_White_Blue_White_Right',
    'Fast_Chase_All_Right',
    'Fade_Cyan_Left',
    'Fade_Red_Green_Blue_Left',
    'Fade_All_Right',
    'Fade_Red_Right',
    'Chase_All_Right'
    ]

class MIC_EFFECTS (Enum):
    # Microphone Effects (0x80-0x87)
    mic_energic = 0x80
    mic_rhythm = 0x81
    mic_spectrum = 0x82
    mic_rolling = 0x83
    mic_effect_4 = 0x84
    mic_effect_5 = 0x85
    mic_effect_6 = 0x86
    mic_effect_7 = 0x87

MIC_EFFECTS_list = [
    'mic_energic',
    'mic_rhythm',
    'mic_spectrum',
    'mic_rolling',
    'mic_effect_4',
    'mic_effect_5',
    'mic_effect_6',
    'mic_effect_7'
    ]

class WEEK_DAYS (Enum):
    monday = 0x01
    tuesday = 0x02
    wednesday = 0x04
    thursday = 0x08
    friday = 0x10
    saturday = 0x20
    sunday = 0x40
    all = (0x01 + 0x02 + 0x04 + 0x08 + 0x10 + 0x20 + 0x40)
    week_days = (0x01 + 0x02 + 0x04 + 0x08 + 0x10)
    weekend_days = (0x20 + 0x40)
    none = 0x00

#print(EFFECTS.blink_red.value)
