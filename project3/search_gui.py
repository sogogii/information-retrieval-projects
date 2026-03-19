import tkinter as tk
from tkinter import ttk, font
import threading
import time

# Import search logic from search.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search import load_resources, search


class SearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CS 121 Search Engine")
        self.root.geometry("900x650")
        self.root.configure(bg="#1e1e2e")

        self._build_ui()
        self._load_in_background()

    def _build_ui(self):
        bg     = "#1e1e2e"
        card   = "#2a2a3e"
        accent = "#7c6af7"
        text   = "#cdd6f4"
        subtle = "#6c7086"

        # Header
        header = tk.Frame(self.root, bg=accent, pady=14)
        header.pack(fill=tk.X)
        tk.Label(header, text="CS 121 Search Engine",
                 font=("Helvetica", 20, "bold"),
                 bg=accent, fg="white").pack()

        # Search bar area
        search_frame = tk.Frame(self.root, bg=bg, pady=20)
        search_frame.pack(fill=tk.X, padx=40)

        self.query_var = tk.StringVar()
        entry_frame = tk.Frame(search_frame, bg=card, padx=10, pady=8,
                               highlightbackground=accent, highlightthickness=2)
        entry_frame.pack(fill=tk.X)

        self.entry = tk.Entry(entry_frame, textvariable=self.query_var,
                              font=("Helvetica", 14), bg=card, fg=text,
                              insertbackground=text, bd=0, relief=tk.FLAT)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", lambda e: self._do_search())

        self.search_btn = tk.Button(entry_frame, text="Search",
                                    font=("Helvetica", 12, "bold"),
                                    bg=accent, fg="white", bd=0,
                                    padx=16, pady=4, cursor="hand2",
                                    command=self._do_search)
        self.search_btn.pack(side=tk.RIGHT)

        # Status label
        self.status_var = tk.StringVar(value="Loading index...")
        tk.Label(self.root, textvariable=self.status_var,
                 font=("Helvetica", 10), bg=bg, fg=subtle).pack()

        # Results area
        results_outer = tk.Frame(self.root, bg=bg, padx=40, pady=10)
        results_outer.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(results_outer, bg=bg, bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(results_outer, orient="vertical",
                                  command=self.canvas.yview)
        self.results_frame = tk.Frame(self.canvas, bg=bg)

        self.results_frame.bind("<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")))

        self.canvas.create_window((0, 0), window=self.results_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.root.bind("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(-1*(e.delta//120), "units"))

        self._colors = {"bg": bg, "card": card, "accent": accent,
                        "text": text, "subtle": subtle}

    def _load_in_background(self):
        def _load():
            load_resources()
            self.status_var.set("Ready — enter a query above")
            self.entry.focus()
        threading.Thread(target=_load, daemon=True).start()

    def _do_search(self):
        query = self.query_var.get().strip()
        if not query:
            return

        self.status_var.set("Searching...")
        self.search_btn.config(state=tk.DISABLED)

        for widget in self.results_frame.winfo_children():
            widget.destroy()

        def _run():
            start = time.time()
            results = search(query, top_k=10)
            elapsed_ms = (time.time() - start) * 1000
            self.root.after(0, lambda: self._show_results(results, query, elapsed_ms))

        threading.Thread(target=_run, daemon=True).start()

    def _show_results(self, results, query, elapsed_ms):
        c = self._colors

        if not results:
            tk.Label(self.results_frame,
                     text="No results found.",
                     font=("Helvetica", 13), bg=c["bg"], fg=c["subtle"]
                     ).pack(pady=20)
        else:
            for rank, (score, url) in enumerate(results, 1):
                card = tk.Frame(self.results_frame, bg=c["card"],
                                padx=16, pady=12)
                card.pack(fill=tk.X, pady=5)

                # Rank + score
                meta = tk.Frame(card, bg=c["card"])
                meta.pack(fill=tk.X)
                tk.Label(meta, text=f"#{rank}",
                         font=("Helvetica", 11, "bold"),
                         bg=c["card"], fg=c["accent"]).pack(side=tk.LEFT)
                tk.Label(meta, text=f"  Score: {score:.4f}",
                         font=("Helvetica", 10),
                         bg=c["card"], fg=c["subtle"]).pack(side=tk.LEFT)

                # URL (clickable-style)
                url_label = tk.Label(card, text=url,
                                     font=("Helvetica", 11),
                                     bg=c["card"], fg="#89b4fa",
                                     cursor="hand2", wraplength=780,
                                     justify=tk.LEFT, anchor="w")
                url_label.pack(fill=tk.X, pady=(4, 0))
                url_label.bind("<Button-1>",
                               lambda e, u=url: self._open_url(u))

        self.status_var.set(
            f"{len(results)} results for '{query}' ({elapsed_ms:.1f}ms)")
        self.search_btn.config(state=tk.NORMAL)

    def _open_url(self, url):
        import webbrowser
        webbrowser.open(url)


def main():
    root = tk.Tk()
    app = SearchApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()