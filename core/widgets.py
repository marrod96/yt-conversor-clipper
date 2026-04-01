"""
Reusable custom widgets for the GUI
"""
import customtkinter as ctk
from .config import COLORS as C


class SectionFrame(ctk.CTkFrame):
    """A frame with a title and bordered styling."""
    def __init__(self, master, title="", **kw):
        super().__init__(master, fg_color=C["panel"], corner_radius=12,
                         border_width=1, border_color=C["border"], **kw)
        if title:
            ctk.CTkLabel(self, text=title,
                         font=ctk.CTkFont("Helvetica", 12, "bold"),
                         text_color=C["sub"]).pack(anchor="w", padx=16, pady=(12, 0))


class LabeledEntry(ctk.CTkFrame):
    """A frame containing a label and an entry field."""
    def __init__(self, master, label, placeholder="", **kw):
        super().__init__(master, fg_color="transparent", **kw)
        ctk.CTkLabel(self, text=label, width=110, anchor="w",
                     font=ctk.CTkFont("Helvetica", 13),
                     text_color=C["text"]).pack(side="left")
        self.entry = ctk.CTkEntry(self, placeholder_text=placeholder,
                                  font=ctk.CTkFont("Helvetica", 13),
                                  height=36, corner_radius=8,
                                  border_color=C["border"],
                                  fg_color=C["bg"])
        self.entry.pack(side="left", fill="x", expand=True)

    def get(self):
        return self.entry.get()

    def set(self, v):
        self.entry.delete(0, "end")
        self.entry.insert(0, v)

    def configure(self, **kw):
        self.entry.configure(**kw)


class StatusBar(ctk.CTkFrame):
    """Status bar showing current application state."""
    def __init__(self, master, **kw):
        super().__init__(master, height=32, fg_color=C["border"],
                         corner_radius=0, **kw)
        self.label = ctk.CTkLabel(self, text="Listo.", anchor="w",
                                  font=ctk.CTkFont("Helvetica", 12),
                                  text_color=C["sub"])
        self.label.pack(side="left", padx=12)
        self.dot = ctk.CTkLabel(self, text="●", text_color=C["muted"],
                                font=ctk.CTkFont("Helvetica", 12))
        self.dot.pack(side="right", padx=12)

    def set(self, msg: str, color: str = None):
        """Update status message and optional indicator color."""
        self.label.configure(text=msg)
        if color:
            self.dot.configure(text_color=color)
        else:
            self.dot.configure(text_color=C["muted"])
