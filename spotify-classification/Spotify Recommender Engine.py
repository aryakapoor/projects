#!/usr/bin/env python
# coding: utf-8

# In[44]:


od.download("https://www.kaggle.com/geomack/spotifyclassification", force=True)


# In[45]:


os.getcwd()


# In[46]:


songs=pd.read_csv('/Users/aryakapoor/Downloads/data.csv')


# In[47]:


songs


# In[62]:


import numpy as np
import pandas as pd

from sklearn import tree
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split

from matplotlib import pyplot as plt
from sklearn.tree import export_graphviz
import pydotplus
import seaborn as sns
import io
from scipy import misc
import imageio


# In[63]:


train,test=train_test_split(songs, test_size=0.15)


# In[64]:


red_blue=['#1985FE', '#EF4836']
palette=sns.color_palette(red_blue)
sns.set_palette(palette)
sns.set_style("white")


# In[65]:


pos_tempo=songs[songs['target']==1]['tempo']
neg_tempo=songs[songs['target']==0]['tempo']

pos_dance=songs[songs['target']==1]['danceability']
neg_dance=songs[songs['target']==0]['danceability']

pos_acous=songs[songs['target']==1]['acousticness']
neg_acous=songs[songs['target']==0]['acousticness']

pos_dur=songs[songs['target']==1]['duration_ms']
neg_dur=songs[songs['target']==0]['duration_ms']

pos_en=songs[songs['target']==1]['energy']
neg_en=songs[songs['target']==0]['energy']

pos_key=songs[songs['target']==1]['key']
neg_key=songs[songs['target']==0]['key']

pos_live=songs[songs['target']==1]['liveness']
neg_live=songs[songs['target']==0]['liveness']

pos_loud=songs[songs['target']==1]['loudness']
neg_loud=songs[songs['target']==0]['loudness']

pos_speech=songs[songs['target']==1]['speechiness']
neg_speech=songs[songs['target']==0]['speechiness']

pos_valence=songs[songs['target']==1]['valence']
neg_valence=songs[songs['target']==0]['valence']

pos_inst=songs[songs['target']==1]['instrumentalness']
neg_inst=songs[songs['target']==0]['instrumentalness']


# In[80]:


fig2=plt.figure(figsize=(15,15))

ax3=fig2.add_subplot(331)
ax3.set_xlabel('Danceability')
ax3.set_ylabel('Count')
ax3.set_title('Song Danceability Target Distribution')
pos_dance.hist(alpha=0.5, bins=30)
neg_dance.hist(alpha=0.7,bins=30)

ax5=fig2.add_subplot(332)
ax5.set_xlabel('Duration')
ax5.set_ylabel('Count')
ax5.set_title('Song Duration Target Distribution')
pos_dur.hist(alpha=0.5, bins=30)
neg_dur.hist(alpha=0.5,bins=30)

ax7=fig2.add_subplot(333)
pos_loud.hist(alpha=0.5, bins=30)
ax7.set_xlabel('Loudness')
ax7.set_ylabel('Count')
ax7.set_title("Song Loudness Like Distribution")
neg_loud.hist(alpha=0.5, bins=30)

ax9=fig2.add_subplot(334)
pos_speech.hist(alpha=0.5, bins=30)
ax9.set_xlabel('Speech')
ax9.set_ylabel('Count')
ax9.set_title("Song Speech Like Distribution")
neg_speech.hist(alpha=0.5, bins=30)

ax11=fig2.add_subplot(335)
pos_valence.hist(alpha=0.5, bins=30)
ax11.set_xlabel('Valence')
ax11.set_ylabel('Count')
ax11.set_title("Song Valence Like Distribution")
neg_valence.hist(alpha=0.5, bins=30)

ax13=fig2.add_subplot(336)
pos_en.hist(alpha=0.5, bins=30)
ax13.set_xlabel('Energy')
ax13.set_ylabel('Count')
ax13.set_title("Song Energy Like Distribution")
neg_en.hist(alpha=0.5, bins=30)

ax15=fig2.add_subplot(337)
pos_acous.hist(alpha=0.5, bins=30)
ax15.set_xlabel('Acousticness')
ax15.set_ylabel('Count')
ax15.set_title("Song Acousticness Like Distribution")
neg_acous.hist(alpha=0.5, bins=30)


ax17=fig2.add_subplot(338)
pos_key.hist(alpha=0.5, bins=30)
ax17.set_xlabel('Key')
ax17.set_ylabel('Count')
ax17.set_title("Song Key Like Distribution")
neg_key.hist(alpha=0.5, bins=30)


ax20=fig2.add_subplot(339)
pos_inst.hist(alpha=0.5, bins=30)
ax20.set_xlabel('Instrumentalness')
ax20.set_ylabel('Count')
ax20.set_title("Song Instrumentalness Like Distribution")
neg_inst.hist(alpha=0.5, bins=30)


# In[68]:


x=DecisionTreeClassifier(min_samples_split=100)


# In[69]:


features=['acousticness', 'danceability', 'duration_ms', 'energy', 'instrumentalness', 'key', 'loudness', 'speechiness', 'valence']


# In[70]:


x_train=train[features]
y_train=train['target']

x_test=test[features]
y_test=test['target']


# In[72]:


decision_tree=x.fit(x_train,y_train)

def show_tree(tree, features, path):
    f=io.StringIO()
    export_graphviz(tree,out_file=f,feature_names=features)
    pydotplus.graph_from_dot_data(f.getvalue()).write_png(path)
    img=imageio.imread(path)
    plt.rcParams['figure.figsize']=(20,20)
    plt.imshow(img)

show_tree(decision_tree, features, 'dec_tree_01.png')


# In[76]:


y_pred=x.predict(x_test)
y_pred


# In[77]:


from sklearn.metrics import accuracy_score
from sklearn.tree import export_graphviz


# In[78]:


score= accuracy_score(y_pred, y_test)*100


# In[79]:


score


# In[ ]:




