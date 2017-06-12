import sys
sys.path.insert(0, '/home/jack/Documents/openstaxTextbook/API')
import Tkinter as tk
import time
import pandas as pd
import content_helper as ch

# read an example JSON file
path = '/home/jack/Documents/openstaxTextbook/output/biology/tagged_txt_by_ch_mo/'
c = 1
m = 1
temp_json = ch.import_json(path, c, m)
# set workspace path
workspace_path = '/home/jack/Documents/openstaxTextbook/data/biology/' # VARIABLE

# read the content file
f = workspace_path+'content_augment_terms_by_chapter.csv'
df = pd.read_csv(f)
# print(df[df['chapter']==1]['p_content'][0])
temp_content = list(df[(df['chapter']==1) & (df['module']==1)]['p_content'])[0]
counter = 0

def disp_sent(label):
    counter = 0
    def count():
        global counter
        sent = temp_json['sentences'][counter]
        sent_begin_idx = sent['tokens'][0]['characterOffsetBegin']
        sent_end_idx = sent['tokens'][-1]['characterOffsetEnd']
        sent_text = temp_content[sent_begin_idx:sent_end_idx]
        label.config(text=sent_text)
        label.after(2000, count)
        counter += 1

    count()

root = tk.Tk()
root.title("Counting Seconds")
label = tk.Label(root, fg="dark green")
label.pack()
disp_sent(label)
button = tk.Button(root, text='Stop', width=25, command=root.destroy)
button.pack()
root.mainloop()