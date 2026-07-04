"""
Музыкальный плеер с поддержкой пользовательского Canvas (видео-фон трека)
Технологии: Flet (Python -> нативный Android/Desktop через Flutter)

Запуск на компьютере для теста:
    pip install flet
    flet run main.py

Сборка под Android (когда будешь готов):
    flet build apk

Структура данных трека хранится в data/library.json
Медиафайлы (аудио/обложки/canvas) копируются в data/media/
"""

import flet as ft
import json
import os
import shutil
import uuid

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
MEDIA_DIR = os.path.join(DATA_DIR, "media")
LIBRARY_FILE = os.path.join(DATA_DIR, "library.json")

os.makedirs(MEDIA_DIR, exist_ok=True)


def load_library():
    if os.path.exists(LIBRARY_FILE):
        with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_library(tracks):
    with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
        json.dump(tracks, f, ensure_ascii=False, indent=2)


def copy_to_media(src_path: str) -> str:
    """Копирует файл в папку media с уникальным именем, возвращает новое имя файла."""
    ext = os.path.splitext(src_path)[1]
    new_name = f"{uuid.uuid4().hex}{ext}"
    dst_path = os.path.join(MEDIA_DIR, new_name)
    shutil.copy(src_path, dst_path)
    return new_name


def main(page: ft.Page):
    page.title = "Мой плеер"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0f0f14"
    page.padding = 0
    page.window.width = 400
    page.window.height = 800

    tracks = load_library()
    current_index = {"value": None}

    audio_player = ft.Audio(src="", autoplay=False, on_state_changed=lambda e: None)
    page.overlay.append(audio_player)

    # ---------- Диалоги выбора файлов ----------
    pending_track = {}

    audio_picker = ft.FilePicker()
    cover_picker = ft.FilePicker()
    canvas_picker = ft.FilePicker()
    page.overlay.extend([audio_picker, cover_picker, canvas_picker])

    def on_audio_picked(e: ft.FilePickerResultEvent):
        if e.files:
            f = e.files[0]
            pending_track["audio_name"] = copy_to_media(f.path)
            pending_track["title"] = os.path.splitext(f.name)[0]
            title_field.value = pending_track["title"]
            status_text.value = f"Аудио выбрано: {f.name}"
            page.update()

    def on_cover_picked(e: ft.FilePickerResultEvent):
        if e.files:
            f = e.files[0]
            pending_track["cover_name"] = copy_to_media(f.path)
            status_text.value = f"Обложка выбрана: {f.name}"
            page.update()

    def on_canvas_picked(e: ft.FilePickerResultEvent):
        if e.files:
            f = e.files[0]
            pending_track["canvas_name"] = copy_to_media(f.path)
            status_text.value = f"Canvas выбран: {f.name}"
            page.update()

    audio_picker.on_result = on_audio_picked
    cover_picker.on_result = on_cover_picked
    canvas_picker.on_result = on_canvas_picked

    title_field = ft.TextField(label="Название трека", width=300)
    artist_field = ft.TextField(label="Исполнитель", width=300)
    status_text = ft.Text("", size=12, color="#9aa0a6")

    def save_pending_track(e):
        if "audio_name" not in pending_track:
            status_text.value = "Сначала выбери аудиофайл!"
            page.update()
            return
        track = {
            "id": uuid.uuid4().hex,
            "title": title_field.value or pending_track.get("title", "Без названия"),
            "artist": artist_field.value or "Неизвестен",
            "audio": pending_track["audio_name"],
            "cover": pending_track.get("cover_name"),
            "canvas": pending_track.get("canvas_name"),
        }
        tracks.append(track)
        save_library(tracks)
        pending_track.clear()
        title_field.value = ""
        artist_field.value = ""
        status_text.value = "Трек добавлен!"
        add_dialog.open = False
        refresh_library()
        page.update()

    add_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Добавить трек"),
        content=ft.Column(
            [
                ft.ElevatedButton(
                    "Выбрать аудио (mp3/wav)",
                    icon=ft.Icons.AUDIOTRACK,
                    on_click=lambda e: audio_picker.pick_files(
                        allowed_extensions=["mp3", "wav", "m4a", "flac"]
                    ),
                ),
                ft.ElevatedButton(
                    "Выбрать обложку",
                    icon=ft.Icons.IMAGE,
                    on_click=lambda e: cover_picker.pick_files(
                        allowed_extensions=["jpg", "jpeg", "png"]
                    ),
                ),
                ft.ElevatedButton(
                    "Выбрать Canvas (видео)",
                    icon=ft.Icons.MOVIE,
                    on_click=lambda e: canvas_picker.pick_files(
                        allowed_extensions=["mp4", "gif"]
                    ),
                ),
                title_field,
                artist_field,
                status_text,
            ],
            tight=True,
            spacing=10,
        ),
        actions=[
            ft.TextButton("Отмена", on_click=lambda e: close_dialog()),
            ft.ElevatedButton("Сохранить", on_click=save_pending_track),
        ],
    )
    page.overlay.append(add_dialog)

    def close_dialog():
        add_dialog.open = False
        page.update()

    def open_add_dialog(e):
        pending_track.clear()
        title_field.value = ""
        artist_field.value = ""
        status_text.value = ""
        add_dialog.open = True
        page.update()

    # ---------- Экран плеера ----------
    now_playing_bg = ft.Container(expand=True)
    now_playing_title = ft.Text("Выбери трек", size=20, weight=ft.FontWeight.BOLD)
    now_playing_artist = ft.Text("", size=14, color="#9aa0a6")
    play_icon_btn = ft.IconButton(icon=ft.Icons.PLAY_ARROW, icon_size=48, on_click=lambda e: toggle_play())

    is_playing = {"value": False}

    def toggle_play():
        if current_index["value"] is None:
            return
        if is_playing["value"]:
            audio_player.pause()
            play_icon_btn.icon = ft.Icons.PLAY_ARROW
        else:
            audio_player.resume()
            play_icon_btn.icon = ft.Icons.PAUSE
        is_playing["value"] = not is_playing["value"]
        page.update()

    def play_track(idx):
        current_index["value"] = idx
        track = tracks[idx]
        audio_path = os.path.join(MEDIA_DIR, track["audio"])
        audio_player.src = audio_path
        audio_player.play()
        is_playing["value"] = True
        play_icon_btn.icon = ft.Icons.PAUSE

        now_playing_title.value = track["title"]
        now_playing_artist.value = track["artist"]

        # Canvas в приоритете над обложкой
        if track.get("canvas"):
            canvas_path = os.path.join(MEDIA_DIR, track["canvas"])
            now_playing_bg.content = ft.Video(
                playlist=[ft.VideoMedia(canvas_path)],
                autoplay=True,
                fill_color="black",
                aspect_ratio=9 / 16,
                muted=True,
                on_loaded=None,
            ) if hasattr(ft, "Video") else ft.Image(
                src=os.path.join(MEDIA_DIR, track["cover"]) if track.get("cover") else None,
                fit=ft.ImageFit.COVER,
            )
        elif track.get("cover"):
            now_playing_bg.content = ft.Image(
                src=os.path.join(MEDIA_DIR, track["cover"]),
                fit=ft.ImageFit.COVER,
                expand=True,
            )
        else:
            now_playing_bg.content = ft.Container(
                bgcolor="#1c1c24",
                content=ft.Icon(ft.Icons.MUSIC_NOTE, size=100, color="#4a4a55"),
                alignment=ft.alignment.center,
                expand=True,
            )
        page.update()

    def next_track():
        if current_index["value"] is None or not tracks:
            return
        idx = (current_index["value"] + 1) % len(tracks)
        play_track(idx)

    def prev_track():
        if current_index["value"] is None or not tracks:
            return
        idx = (current_index["value"] - 1) % len(tracks)
        play_track(idx)

    player_screen = ft.Container(
        expand=True,
        content=ft.Stack(
            [
                now_playing_bg,
                ft.Container(
                    alignment=ft.alignment.bottom_center,
                    padding=20,
                    content=ft.Column(
                        [
                            ft.Container(
                                bgcolor="#00000099",
                                border_radius=12,
                                padding=15,
                                content=ft.Column(
                                    [
                                        now_playing_title,
                                        now_playing_artist,
                                        ft.Row(
                                            [
                                                ft.IconButton(icon=ft.Icons.SKIP_PREVIOUS, on_click=lambda e: prev_track()),
                                                play_icon_btn,
                                                ft.IconButton(icon=ft.Icons.SKIP_NEXT, on_click=lambda e: next_track()),
                                            ],
                                            alignment=ft.MainAxisAlignment.CENTER,
                                        ),
                                    ]
                                ),
                            )
                        ]
                    ),
                ),
            ]
        ),
    )

    # ---------- Экран библиотеки ----------
    library_list = ft.ListView(expand=True, spacing=5, padding=10)

    def make_track_tile(idx, track):
        has_canvas = "🎬" if track.get("canvas") else ""
        return ft.ListTile(
            leading=ft.Icon(ft.Icons.MUSIC_NOTE),
            title=ft.Text(f"{track['title']} {has_canvas}"),
            subtitle=ft.Text(track["artist"]),
            on_click=lambda e, i=idx: (play_track(i), go_to_player()),
            trailing=ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                on_click=lambda e, i=idx: delete_track(i),
            ),
        )

    def delete_track(idx):
        tracks.pop(idx)
        save_library(tracks)
        refresh_library()
        page.update()

    def refresh_library():
        library_list.controls.clear()
        for i, t in enumerate(tracks):
            library_list.controls.append(make_track_tile(i, t))
        page.update()

    library_screen = ft.Column(
        [
            ft.Container(
                padding=15,
                content=ft.Row(
                    [
                        ft.Text("Моя библиотека", size=22, weight=ft.FontWeight.BOLD),
                        ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_size=32, on_click=open_add_dialog),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ),
            library_list,
        ],
        expand=True,
    )

    # ---------- Навигация ----------
    content_area = ft.Container(content=library_screen, expand=True)

    def go_to_player():
        content_area.content = player_screen
        nav_bar.selected_index = 1
        page.update()

    def go_to_library():
        content_area.content = library_screen
        nav_bar.selected_index = 0
        page.update()

    def on_nav_change(e):
        if e.control.selected_index == 0:
            go_to_library()
        else:
            go_to_player()

    nav_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.LIBRARY_MUSIC, label="Библиотека"),
            ft.NavigationBarDestination(icon=ft.Icons.PLAY_CIRCLE, label="Плеер"),
        ],
        on_change=on_nav_change,
    )

    page.add(
        ft.Column(
            [content_area, nav_bar],
            expand=True,
            spacing=0,
        )
    )

    refresh_library()


if __name__ == "__main__":
    ft.app(target=main)
