import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
from PIL import Image

# Configure customtkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

class SpotifyDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Spotify Playlist Downloader")
        self.geometry("920x720")
        self.resizable(False, False)
        self.checked_items = {}  # key: item ID, value: True/False


        self.font = ("Segoe UI", 14)

        self.download_path = os.getcwd()
        self.tracks = []

        self.setup_ui()

    def setup_ui(self):
        # ========== HEADER WITH LOGOS ==========
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(pady=10, fill="x")

        try:
            spotify_logo = ctk.CTkImage(Image.open("assets/spotify_logo.png"), size=(40, 40))
            logo_img = ctk.CTkImage(Image.open("assets/my_logo.png"), size=(40, 40))
            ctk.CTkLabel(header_frame, image=spotify_logo, text="").pack(side="left", padx=10)
            ctk.CTkLabel(header_frame, text="Spotify Playlist Downloader", font=("Segoe UI", 20, "bold")).pack(side="left", padx=10)
            ctk.CTkLabel(header_frame, image=logo_img, text="").pack(side="right", padx=10)
        except:
            ctk.CTkLabel(header_frame, text="Spotify Playlist Downloader", font=("Segoe UI", 20, "bold")).pack()

        # ========== CLIENT CREDENTIALS ==========
        self.client_id_entry = self.create_entry_with_label("Client ID:")
        self.client_secret_entry = self.create_entry_with_label("Client Secret:")

        # ========== PLAYLIST URL ==========
        self.playlist_url_entry = self.create_entry_with_label("Spotify Playlist URL:")

        # ========== SELECT FOLDER ==========
        folder_button = ctk.CTkButton(self, text="Select Download Folder", font=self.font, command=self.select_folder)
        folder_button.pack(pady=5)

        self.folder_label = ctk.CTkLabel(self, text=f"Download Folder: {self.download_path}", font=("Segoe UI", 12))
        self.folder_label.pack()

        # ========== FETCH TRACKS BUTTON ==========
        ctk.CTkButton(self, text="Fetch Playlist", font=self.font, command=self.fetch_playlist_thread).pack(pady=10)

        # ========== SONG LIST (SCROLLABLE TREEVIEW) ==========
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(pady=10, fill="both", expand=True, padx=10)

        self.song_table = ttk.Treeview(table_frame, columns=("Select", "Track", "Artist"), show="headings", selectmode="none", height=10)
        self.song_table.heading("Select", text="✓")
        self.song_table.heading("Track", text="Track Name")
        self.song_table.heading("Artist", text="Artist")

        # Set column widths
        self.song_table.column("Select", width=50, anchor="center")
        self.song_table.column("Track", width=350)
        self.song_table.column("Artist", width=200)

        self.song_table.pack(side="left", fill="both", expand=True)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.song_table.yview)
        scrollbar.pack(side="right", fill="y")
        self.song_table.configure(yscrollcommand=scrollbar.set)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", font=("Segoe UI", 12), rowheight=30)
        
        self.song_table.bind("<Button-1>", self.toggle_checkbox)


        # ========== DOWNLOAD BUTTONS ==========
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)

        
        # ========== PROGRESS BAR ==========
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.pack(pady=10)

        self.progress = ctk.CTkProgressBar(progress_frame, width=500, height=20)
        self.progress.pack(side="left", padx=10)
        self.progress.set(0)

        self.progress_label = ctk.CTkLabel(progress_frame, text="0%", font=self.font)
        self.progress_label.pack(side="left")
        
        
        self.download_selected_btn = ctk.CTkButton(btn_frame, text="Download Selected",font=self.font, command=self.download_selected_thread)
        self.download_selected_btn.pack(side="left", padx=10)

        self.download_all_btn = ctk.CTkButton(btn_frame, text="Download All",font=self.font, command=self.download_all_thread)
        self.download_all_btn.pack(side="left", padx=10)

    def toggle_checkbox(self, event):
        region = self.song_table.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = self.song_table.identify_column(event.x)
        if column != "#1":  # Only toggle if first column (checkbox)
            return

        row_id = self.song_table.identify_row(event.y)
        if not row_id:
            return

        # Toggle state
        current = self.checked_items.get(row_id, False)
        self.checked_items[row_id] = not current
        new_value = "✔" if not current else "✖"

        # Update display
        values = list(self.song_table.item(row_id, "values"))
        values[0] = new_value
        self.song_table.item(row_id, values=values)

    def create_entry_with_label(self, label_text):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(pady=5)

        ctk.CTkLabel(frame, text=label_text, font=self.font, width=160, anchor="w").pack(side="left", padx=(10, 0))

        entry = ctk.CTkEntry(frame, width=400, font=self.font)
        entry.pack(side="left", padx=5)

        ctk.CTkButton(frame, text="📋", width=30, font=self.font, command=lambda e=entry: self.paste_to_entry(e)).pack(side="left")

        return entry

    def paste_to_entry(self, entry):
        try:
            entry.delete(0, 'end')
            entry.insert(0, self.clipboard_get())
        except:
            pass

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.download_path = folder
            self.folder_label.configure(text=f"Download Folder: {self.download_path}")

    def fetch_playlist_thread(self):
        threading.Thread(target=self.fetch_playlist).start()

    def fetch_playlist(self):
        self.tracks.clear()
        self.song_table.delete(*self.song_table.get_children())

        cid = self.client_id_entry.get().strip()
        secret = self.client_secret_entry.get().strip()
        playlist_url = self.playlist_url_entry.get().strip()

        if not (cid and secret and playlist_url):
            messagebox.showwarning("Input Missing", "Please fill all fields.")
            return

        try:
            client = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=cid, client_secret=secret))
            playlist_id = playlist_url.split("/")[-1].split("?")[0]
            results = client.playlist_tracks(playlist_id)
            for item in results['items']:
                track = item['track']
                name = track['name']
                artist = track['artists'][0]['name']
                self.tracks.append((name, artist))
                item_id = self.song_table.insert("", "end", values=("✖", name, artist))
                self.checked_items[item_id] = False


        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch playlist:\n{e}")

    def download_selected_thread(self):
        threading.Thread(target=self.download_selected).start()

    def download_all_thread(self):
        threading.Thread(target=self.download_all).start()

    def download_selected(self):
        # Build list from checked checkboxes only
        selected = []
        for item_id, checked in self.checked_items.items():
            if checked:
                values = self.song_table.item(item_id)["values"]
                if len(values) >= 3:
                    name = values[1]
                    artist = values[2]
                    selected.append(f"{name} {artist}")

        if not selected:
            messagebox.showinfo("No Selection", "Please select at least one song.")
            return

        # Start download in current thread (called from a background thread already)
        self.download_songs(selected)


    def download_all(self):
        if not self.tracks:
            messagebox.showinfo("Empty List", "No songs to download.")
            return
        search_queries = [f"{name} {artist}" for name, artist in self.tracks]
        self.download_songs(search_queries)


    def download_songs(self, songs):
        songs = list(songs)
        total = len(songs)
        if total == 0:
            return

        # Disable buttons while downloading (if you created them as suggested)
        try:
            if hasattr(self, "download_selected_btn"):
                self.download_selected_btn.configure(state="disabled")
            if hasattr(self, "download_all_btn"):
                self.download_all_btn.configure(state="disabled")
        except:
            pass

        try:
            for i, query in enumerate(songs):
                percent = int((i + 1) / total * 100)
                self.progress.set((i + 1) / total)
                self.progress_label.configure(text=f"{percent}%")

                # Download (blocking) — this runs inside the background thread started by download_selected_thread()
                self.download_song(query)
            self.progress.set(1)
            self.progress_label.configure(text="100%")
            messagebox.showinfo("Done", "Download completed.")
        finally:
            # Re-enable buttons and reset progress after a short delay
            if hasattr(self, "download_selected_btn"):
                self.download_selected_btn.configure(state="normal")
            if hasattr(self, "download_all_btn"):
                self.download_all_btn.configure(state="normal")
            # optional: reset progress after 1s
            # self.after(1000, lambda: (self.progress.set(0), self.progress_label.configure(text="0%")))


    def download_song(self, query):
        opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                ydl.download([f"ytsearch:{query}"])
            except:
                pass

if __name__ == "__main__":
    app = SpotifyDownloaderApp()
    app.mainloop()
