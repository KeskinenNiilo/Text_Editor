import tkinter as tk
from tkinter import filedialog, PhotoImage
import tkinter.messagebox as msgbox
from tkinter.messagebox import askquestion
import ctypes
import ollama
import json
import sys

# Get settings.json, defaults last
try:
    with open('settings.json', 'r') as file:
        settings = json.load(file)
except:
    settings = {}

text_font = settings.get('text_settings', {}).get('text_font', 'Arial')
text_size = settings.get('text_settings', {}).get('text_size', '14')
file_save_on_exit = settings.get('file_settings', {}).get('file_save_on_exit', True)
file_auto_save = settings.get('file_settings', {}).get('file_auto_save', True)
if file_auto_save:
    file_auto_save_interval = settings.get('file_settings', {}).get('file_auto_save_interval', 300)
ai_tools = settings.get('ai_settings', {}).get('ai_tools', False)
if ai_tools:
    spellcheck_model = settings.get('ai_settings', {}).get('spellcheck_model', None)
    gen_model = settings.get('ai_settings', {}).get('gen_model', None)
    spellcheck_prompt = settings.get('ai_settings', {}).get('spellcheck_prompt', '')
    gen_prompt = settings.get('ai_settings', {}).get('gen_prompt', '')

# Less blurry on windows    
if sys.platform == 'win32':
    ctypes.windll.shcore.SetProcessDpiAwareness(1)

# Root window
root = tk.Tk()
root.title('*')
root.geometry('1200x800')
file_name = ''

# Icon, delete if useless or replace icon.png with something else
photo = PhotoImage(file='icon.png')
root.iconphoto(False, photo)

# Text area
text_widget = tk.Text(root, font=(text_font, text_size))
text_widget.pack(fill='both', expand=True)
text_widget.config(undo=True, maxundo=-1)

# Open file, if text in unsaved or already editing a file, asks to save
def open_file():
    global file_name
    text = text_widget.get('1.0', 'end')
    if text.strip() != '' or file_name != '*':
        if save_file_qstn(): save_file()
    file_path = filedialog.askopenfilename()
    if file_path:
        text_widget.delete('1.0', 'end')
        with open(file_path, 'r') as file:
            text_widget.insert('1.0', file.read())
            file_name = file_path
    root.title(file_name)

# Open file specified in call
if len(sys.argv) > 1:
    try:
        with open(sys.argv[1], 'r') as file:
            text_widget.insert('1.0', file.read())
            file_name = sys.argv[1]
            root.title(file_name)
    except FileNotFoundError:
        raise RuntimeError('No file found')

# Save with file dialog
def save_as_file():
    global file_name
    file_path = filedialog.asksaveasfilename()
    if file_path:
        with open(file_path, 'w') as file:
            file.write(text_widget.get('1.0', 'end'))
            file_name = file_path
    root.title(file_name)

# Save if file_name is not "*" or text is not null, if file_name is "*" -> save_as_file
def save_file(event=None):
    global file_name
    text = text_widget.get('1.0', 'end')
    if file_name == '' and text.strip() == '':
        return
    if file_name == '':
        save_as_file()
        return
    with open(file_name, 'w') as file:
        file.write(text)
    root.title(file_name)

# Bind CTRL + S to file save
root.bind('<Control-s>', save_file)

# File save question
def save_file_qstn():
    qstn = msgbox.askquestion('Save', 'Save changes?', icon='question')
    return qstn == 'yes'

# Auto save
def auto_save():
    if file_name and text_widget.edit_modified():
        save_file()
    root.after(file_auto_save_interval * 1000, auto_save)

if file_auto_save: auto_save()

# New file, almost same as open_file
def new_file():
    global file_name
    text = text_widget.get('1.0', 'end-1c').strip()
    if text != '' or file_name != '':
        if save_file_qstn(): save_file()
    file_name = ''
    text_widget.delete('1.0', 'end')
    root.title('*')
# Basic text editing util
def cut():
    text_widget.event_generate('<<Cut>>')
def copy():
    text_widget.event_generate('<<Copy>>')
def paste():
    text_widget.event_generate('<<Paste>>')
def select_all():
    text_widget.tag_add('sel', '1.0', 'end')

root.bind('<Control-z>', lambda e: undo())
root.bind('<Control-y>', lambda e: redo())

# Function to make tidier code
def ai(model_str, prompt, text):
    response = ollama.chat(
            model = model_str,
            messages=[{'role':'user', 'content' : f'{prompt}\n\n{text}'}
            ]
        )
    return response['message']['content']
    
# AI spellcheck, replaces text with "correct" spelling, if false consider changing model
def AIspellcheck():
    if spellcheck_model:
        response = ai(spellcheck_model, spellcheck_prompt, text_widget.get(1.0, 'end'))
        text_widget.delete('1.0', 'end')
        text_widget.insert('end', response)

# Prompts can be edited in settings.json
def AIgenerate():
    if gen_model:
        response = ai(gen_model, gen_prompt, text_widget.get(1.0, 'end'))
        text_widget.delete('1.0', 'end')
        text_widget.insert('end', response)

# Find text
def find_text():
    find_dialog = tk.Toplevel(root)
    find_dialog.title('Find')
    
    tk.Label(find_dialog, text='Find:').grid(row=0, column=0, padx=5, pady=5)
    find_entry = tk.Entry(find_dialog, width=30)
    find_entry.grid(row=0, column=1, padx=5, pady=5)
    
    def find():
        text_widget.tag_remove('found', '1.0', tk.END)
        search_text = find_entry.get()
        if search_text:
            start_pos = '1.0'
            while True:
                start_pos = text_widget.search(search_text, start_pos, stopindex=tk.END)
                if not start_pos:
                    break
                end_pos = f'{start_pos}+{len(search_text)}c'
                text_widget.tag_add('found', start_pos, end_pos)
                start_pos = end_pos
            text_widget.tag_config('found', background='yellow')
    
    tk.Button(find_dialog, text='Find', command=find).grid(row=1, column=1, padx=5, pady=5)
    find_entry.focus_set()

# Undo and redo
def undo():
    try:
        text_widget.edit_undo()
    except:
        pass

def redo():
    try:
        text_widget.edit_redo()
    except:
        pass

# Ask to save file if user has file_save_on_exit as true, 
def quit_app():
    text = text_widget.get('1.0', 'end').strip()
    if file_save_on_exit and (text != '' or file_name != '*'):
        if save_file_qstn(): save_file()
    root.quit()
    root.destroy()

# Override X button to quit_app
root.protocol('WM_DELETE_WINDOW', quit_app);

# Menu bar
menu_bar = tk.Menu(root)

file_menu = tk.Menu(menu_bar, tearoff=0)
file_menu.add_command(label='Open', command=open_file)
file_menu.add_command(label='Save as', command=save_as_file)
file_menu.add_command(label='Save', command=save_file)
file_menu.add_separator()
file_menu.add_command(label='New', command=new_file)
file_menu.add_separator()
file_menu.add_command(label='Exit', command=quit_app)
menu_bar.add_cascade(label='File', menu=file_menu)


edit_menu = tk.Menu(menu_bar, tearoff=0)
edit_menu.add_command(label='Cut', command=cut)
edit_menu.add_command(label='Copy', command=copy)
edit_menu.add_command(label='Paste', command=paste)
edit_menu.add_separator()
edit_menu.add_command(label='Select All', command=select_all)
edit_menu.add_separator()
edit_menu.add_command(label='Find', command=find_text)
menu_bar.add_cascade(label='Edit', menu=edit_menu)
edit_menu.add_command(label='Undo', command=undo, accelerator='Ctrl+Z')
edit_menu.add_command(label='Redo', command=redo, accelerator='Ctrl+Y')
if ai_tools:
    ai_menu = tk.Menu(menu_bar, tearoff=0)
    if spellcheck_model: ai_menu.add_command(label='Spellcheck', command=AIspellcheck)
    if gen_model: ai_menu.add_command(label='Generate', command=AIgenerate)
    menu_bar.add_cascade(label='AI', menu=ai_menu)

root.config(menu=menu_bar)

# Main window loop
root.mainloop()
