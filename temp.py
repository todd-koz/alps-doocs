#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  2 11:50:27 2022

@author: todd
"""

import tkinter as tk

class ChannelSelect(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        channels = {"NR TEWS ADC": ["NR/CH_1.00","NR/CH_1.01","NR/CH_1.02","NR/CH_1.03","NR/CH_1.04","NR/CH_1.05"],
                 "CH TEWS ADC": ["HN/CH_1.00","HN/CH_1.01"],
                 "NL TEWS ADC": ["NL/CH_1.00","NL/CH_1.01"]}

        self.the_value = tk.StringVar()
        self.the_value.set("a")

        self.menubutton = tk.Menubutton(self, textvariable=self.the_value, indicatoron=True)
        self.topMenu = tk.Menu(self.menubutton, tearoff=False)
        self.menubutton.configure(menu=self.topMenu)

        for key in sorted(channels.keys()):
            menu = tk.Menu(self.topMenu)
            self.topMenu.add_cascade(label=key, menu=menu)
            for value in channels[key]:
                menu.add_radiobutton(label=value, variable = self.the_value, value=value)

        self.menubutton.pack()

if __name__ == "__main__":
    root = tk.Tk()
    ChannelSelect(root).pack(fill="both", expand=True)
    root.mainloop()