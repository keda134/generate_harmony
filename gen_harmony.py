from mido import Message, MidiTrack, MidiFile, MetaMessage

# スケールの間隔（半音数）を定義
major_scale = [2, 2, 1, 2, 2, 2, 1]  # メジャースケール
minor_scale = [2, 1, 2, 2, 1, 2, 2]  # マイナースケール

def blue_note(note, scale, mode="snap"):
    if mode == 'snap':
        #スケール内の音にスナップ
        note_in_scale = min(scale, key=lambda x: abs(x - note)) #半音低い音にスナップ
        return note_in_scale
    
    elif mode == 'move':
        #そのまま移動
        return note
    
    else:
        raise ValueError("Error")

# スケールに基づいてハーモニーを生成する関数
def generate_harmony(root_note, scale_intervals, melody, interval, blue_note_mode):
    # ルート音からスケールを生成（複数オクターブ考慮）
    scale = [root_note]
    last_note = root_note

    # 上方向のスケールを生成
    while last_note <= 127:  # MIDIノート番号の上限
        for i in scale_intervals:
            last_note += i
            if last_note <= 127:
                scale.append(last_note)
            else:
                break

     # 下方向のスケールも生成
    last_note = root_note
    while last_note >= 0:  # MIDIノート番号の下限
        for i in reversed(scale_intervals):
            last_note -= i
            if last_note >= 0:
                scale.insert(0, last_note)
            else:
                break

    harmony = []
    for note_on, note_off in melody:
        note = note_on.note
        # メロディの音がスケール内にあるか確認
        if note in scale:
            # スケール内の全てのインデックスを取得
            indices = [i for i, x in enumerate(scale) if x == note]
            
            # 最も近いオクターブのインデックスを使用
            index = min(indices, key=lambda x: abs(x - len(scale_intervals)))  # 現在のオクターブに最も近いもの
            
            # 指定された度数に基づいてハーモニーを生成
            harmonized_index = index + interval  # ここでは剰余を取らない
            
            # 範囲外の場合は調整
            if harmonized_index < 0 or harmonized_index >= len(scale):
                harmonized_note = note
            else:
                harmonized_note = scale[harmonized_index]

            harmonized_note_on = Message('note_on', note=harmonized_note, velocity=note_on.velocity, time=note_on.time)
            harmonized_note_off = Message('note_off', note=harmonized_note, velocity=note_off.velocity, time=note_off.time)
            harmony.append((harmonized_note_on, harmonized_note_off))

        else:
            # ブルーノートの処理
            moved_note = note + interval
            harmonized_note = blue_note(moved_note, scale, blue_note_mode)
            harmonized_note_on = Message('note_on', note=harmonized_note, velocity=note_on.velocity, time=note_on.time)
            harmonized_note_off = Message('note_off', note=harmonized_note, velocity=note_off.velocity, time=note_off.time)
            harmony.append((harmonized_note_on, harmonized_note_off))
    
    return harmony

def save_harmony(harmony, filename):
    new_midi = MidiFile()
    new_track = MidiTrack()
    new_midi.tracks.append(new_track)

    for i, (note_on, note_off) in enumerate(harmony):
        harmonized_note_on, harmonized_note_off = note_on, note_off  # ハーモニーのnote_onとnote_off

        # 元のメロディから時間とベロシティを取得
        time_on = note_on.time
        time_off = note_off.time

        # MIDIトラックにメッセージを追加
        new_track.append(Message('note_on', note=harmonized_note_on.note, velocity=harmonized_note_on.velocity, time=time_on))
        new_track.append(Message('note_off', note=harmonized_note_off.note, velocity=harmonized_note_off.velocity, time=time_off))

    new_midi.save(filename)

# ユーザー選択
scale_choice = input("Choose a scale (major/minor): ").strip().lower()

# 選択結果
if scale_choice == "major":
    chosen_scale = major_scale
elif scale_choice == "minor":
    chosen_scale = minor_scale
else:
    print("入力ミスです。メジャースケールに設定されます。")
    chosen_scale = major_scale

# ユーザー選択
blue_note_choice = input("Choose a scale (snap/move): ").strip().lower()

# 選択結果
if blue_note_choice == "snap":
    blue_note_mode = "snap"
elif blue_note_choice == "move":
    blue_note_mode = "move"
else:
    print("入力ミスです。snapに設定されます。")
    blue_note_mode = "snap"

# MIDIファイルを読み込む
midi = MidiFile('test_midi.mid')

# メロディラインとテンポを保存するためのリスト
melody_pairs = []  #note_onとnote_offのペアを格納するリスト
tempo = None
track = midi.tracks[0]
note_on = None
prev_time = 0
for msg in track:
    if msg.type == 'set_tempo':
        tempo = msg.tempo
    if msg.type == 'note_on':
        if note_on is not None:  # 前のnote_onがnote_offなしであれば
            note_off_time = msg.time - prev_time  # 追加：note_offの時間を計算
            note_off = Message('note_off', note=note_on.note, velocity=note_on.velocity, time=note_off_time)
            melody_pairs.append((note_on, note_off))
        note_on = msg
        prev_time = msg.time  # 追加：前のメッセージの時間を更新
    elif msg.type == 'note_off':
        if note_on is not None and note_on.note == msg.note:
            melody_pairs.append((note_on, msg))
            note_on = None

# デバッグ出力
#print("Melody Pairs:", melody_pairs)

if tempo is None:
    tempo = 500000
print("Tempo before setting:", tempo)

melody_events = []
for note_on, note_off in melody_pairs:
    note = note_on.note
    velocity = note_on.velocity
    time = note_on.time  # ここではnote_onの時間を使用しています。
    melody_events.append((note, velocity, time))

scale_root = int(input("スケールのルート音を一覧から選んでください(MIDI番号)。 (C:60, C#: 61, D:61, D#: 63, E:64 F:65 F#:66 G:67 G#:68 A:69 A#:70 B:71 ): "))

# 三度上のハモリ生成
upper_harmony = generate_harmony(scale_root, chosen_scale, melody_pairs, 2, blue_note_mode)

# 三度下のハモリ生成
lower_harmony = generate_harmony(scale_root, chosen_scale, melody_pairs, -2, blue_note_mode)

# 三度上のハモリ保存
save_harmony(upper_harmony, 'upper_harmony_output.mid')

# 三度下のハモリ保存
save_harmony(lower_harmony, 'lower_harmony_output.mid')

print("Upper harmony: OK")
print("Lower harmony: OK")
#print("Upper harmony: ", upper_harmony)