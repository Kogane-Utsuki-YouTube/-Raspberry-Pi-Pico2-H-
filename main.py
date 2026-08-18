from machine import Pin, PWM
import time
import random

# ==========================================
# ピン設定 & ボタン割り当て (1ボタン = 1音)
# ==========================================
BUTTON_CONFIGS = [
    {"pin": Pin(0, Pin.IN, Pin.PULL_UP), "freq": 262, "name": "ド (上)"},
    {"pin": Pin(1, Pin.IN, Pin.PULL_UP), "freq": 294, "name": "レ (左)"},
    {"pin": Pin(3, Pin.IN, Pin.PULL_UP), "freq": 330, "name": "ミ (下)"},
    {"pin": Pin(4, Pin.IN, Pin.PULL_UP), "freq": 349, "name": "ファ (右)"},
    {"pin": Pin(5, Pin.IN, Pin.PULL_UP), "freq": 392, "name": "ソ (赤/A)"},
    {"pin": Pin(6, Pin.IN, Pin.PULL_UP), "freq": 440, "name": "ラ (灰/B)"},
]

sw_mode = Pin(14, Pin.IN, Pin.PULL_UP)
speaker = PWM(Pin(15))

SWITCH_INTERVAL_MS = 8

# ==========================================
# ハイスコア（メモリ上のみ保持。電源を切るとリセットされます）
# ==========================================
highscore = 0

# ==========================================
# 音出し補助関数
# ==========================================
def play_tone(freq, duration_ms):
    if freq == 0:
        speaker.duty_u16(0)
        time.sleep_ms(duration_ms)
    else:
        speaker.freq(freq)
        speaker.duty_u16(16384)
        time.sleep_ms(duration_ms)
        speaker.duty_u16(0)

def set_tone(freq):
    if freq == 0:
        speaker.duty_u16(0)
    else:
        speaker.freq(freq)
        speaker.duty_u16(16384)

def stop_tone():
    speaker.duty_u16(0)

def play_chord_fast(freqs, duration_ms, switch_ms=6):
    """複数周波数を高速切り替えして和音風に鳴らす"""
    if not freqs:
        time.sleep_ms(duration_ms)
        return
    end_time = time.ticks_add(time.ticks_ms(), duration_ms)
    idx = 0
    last_switch = time.ticks_ms()
    while time.ticks_diff(end_time, time.ticks_ms()) > 0:
        now = time.ticks_ms()
        if time.ticks_diff(now, last_switch) >= switch_ms:
            set_tone(freqs[idx % len(freqs)])
            idx += 1
            last_switch = now
        time.sleep_ms(1)
    stop_tone()

def play_slide(f_start, f_end, duration_ms, steps=12):
    """周波数を滑らかに変化させるスライド音（グリッサンド演出）"""
    step_time = max(duration_ms // steps, 5)
    for i in range(steps + 1):
        f = f_start + (f_end - f_start) * i // steps
        speaker.freq(int(f))
        speaker.duty_u16(16384)
        time.sleep_ms(step_time)
    speaker.duty_u16(0)

def get_pressed_buttons():
    return [idx for idx, cfg in enumerate(BUTTON_CONFIGS) if cfg["pin"].value() == 0]

def get_pressed_button():
    pressed = get_pressed_buttons()
    return pressed[0] if pressed else None

def wait_for_button_release(btn_idx):
    while BUTTON_CONFIGS[btn_idx]["pin"].value() == 0:
        time.sleep_ms(10)

def get_speed_for_score(score):
    speed = 350 - (score * 10)
    return max(speed, 150)

def play_sequence(sequence, speed_ms=350):
    print("\n--- 音をよく覚えてね！ ---")
    time.sleep_ms(500)
    for idx in sequence:
        cfg = BUTTON_CONFIGS[idx]
        play_tone(cfg["freq"], speed_ms)
        time.sleep_ms(max(speed_ms // 2, 80))

# ---- 各種効果音 ----

def start_game_sound():
    """ゲーム開始の合図（上昇アルペジオ + 和音締め）"""
    for f in (330, 392, 440, 523):
        play_tone(f, 55)
    play_chord_fast([523, 659, 784], 150)

def stage_clear_sound(combo_level=0):
    """正解音：ピッチが上がる2音+キラッと光る高音の装飾"""
    base = [523, 659]
    shift = min(combo_level, 12)
    factor = 2 ** (shift / 12)
    f1 = int(base[0] * factor)
    f2 = int(base[1] * factor)
    play_tone(f1, 70)
    play_tone(f2, 90)
    play_tone(int(f2 * 1.25), 60)

def wrong_input_sound():
    """入力ミス：不協和音→下降ブザー"""
    play_chord_fast([220, 233], 180)
    play_slide(200, 100, 200, steps=8)

def game_over_sound(score):
    global highscore
    print(f"\n💥 ブッブー！残念！")
    print(f"🏆 スコア: {score}音 連続正解！")

    is_new_record = score > highscore
    if is_new_record:
        highscore = score  # メモリ上のみ更新（保存はしない）

    play_slide(392, 220, 300, steps=10)
    play_chord_fast([220, 262], 250)
    play_tone(196, 400)

    if is_new_record:
        print("🎉 ニューレコード！！（このセッション中のみ有効）")
        highscore_fanfare()

    print(f"👑 ハイスコア: {highscore}音")
    time.sleep(1)

def highscore_fanfare():
    """ハイスコア更新：豪華な上昇アルペジオ + 和音とキラキラ装飾"""
    notes = (392, 440, 523, 659, 784, 880, 1047)
    for f in notes:
        play_tone(f, 75)
        time.sleep_ms(10)
    play_chord_fast([523, 659, 784, 1047], 300)
    for f in (1047, 1175, 1319, 1568):
        play_tone(f, 45)

def countdown_beep(n):
    freqs = {3: 440, 2: 440, 1: 440, 0: 880}
    play_tone(freqs.get(n, 440), 120)

# ==========================================
# 自由演奏モードの処理
# ==========================================
def run_free_play_mode():
    print("\n==================================")
    print("🎹 自由演奏モード (Free Play) 🎹")
    print("複数ボタン同時押しで和音風の音も出せます！")
    print("==================================")

    last_switch = time.ticks_ms()
    tone_index = 0
    last_pressed_list = []

    while sw_mode.value() == 0:
        pressed_list = get_pressed_buttons()

        if pressed_list != last_pressed_list:
            names = [BUTTON_CONFIGS[i]["name"] for i in pressed_list]
            if names:
                print(f"演奏: {', '.join(names)}")
            tone_index = 0
            last_pressed_list = pressed_list

        if not pressed_list:
            stop_tone()
        else:
            now = time.ticks_ms()
            if time.ticks_diff(now, last_switch) >= SWITCH_INTERVAL_MS:
                tone_index = (tone_index + 1) % len(pressed_list)
                cfg = BUTTON_CONFIGS[pressed_list[tone_index]]
                set_tone(cfg["freq"])
                last_switch = now

        time.sleep_ms(1)

    stop_tone()
    print("\n自由演奏モード終了")

# ==========================================
# メインループ
# ==========================================
while True:
    if sw_mode.value() == 0:
        run_free_play_mode()
        continue

    print("\n==================================")
    print("🎵 6ボタン・音の記憶ゲーム 🎵")
    print(f"👑 現在のハイスコア: {highscore}音（このセッションのみ）")
    print("どれかボタンを押すとスタート！")
    print("==================================")

    started = False
    while sw_mode.value() != 0:
        btn = get_pressed_button()
        if btn is not None:
            start_game_sound()
            wait_for_button_release(btn)
            started = True
            break
        time.sleep_ms(20)

    if not started:
        continue

    sequence = []
    score = 0

    while sw_mode.value() != 0:
        sequence.append(random.randint(0, 5))
        speed_ms = get_speed_for_score(score)

        play_sequence(sequence, speed_ms)

        player_inputs = []
        print(f"👉 【{len(sequence)}音】入力が終わるまで待機中...")

        aborted = False
        for step in range(len(sequence)):
            while True:
                if sw_mode.value() == 0:
                    aborted = True
                    break

                pressed = get_pressed_button()
                if pressed is not None:
                    cfg = BUTTON_CONFIGS[pressed]
                    print(f"[{step+1}/{len(sequence)}] 入力: {cfg['name']}")
                    play_tone(cfg["freq"], 200)
                    player_inputs.append(pressed)

                    wait_for_button_release(pressed)
                    break
                time.sleep_ms(10)

            if aborted:
                break

        if aborted:
            break

        time.sleep_ms(300)

        if player_inputs == sequence:
            score += 1
            print(f"✨ 正解！ 全て一致しました！ 次は {score + 1} 音！")
            stage_clear_sound(score)
            time.sleep_ms(500)
        else:
            wrong_input_sound()
            game_over_sound(score)
            break
