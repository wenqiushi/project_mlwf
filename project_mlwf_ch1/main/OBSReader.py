
# coding: utf-8

# In[22]:


import pandas as pd
import dateparser
import datetime
import os
import re
import geopandas as gpd
from shapely.geometry import Point


# In[75]:


OBSTIME = '(\d+)(\.\w+)'
P = re.compile("(SYNOP)%s" %(OBSTIME))
GUANGDONG = gpd.read_file(os.path.abspath('./../read_binary/data/XZQ_D.shp'))
class obs_from_file(object):
    def __init__(self,filename,nav=-888888.0,sep=' ',incr=1):
        self.filename  = filename
        self._find_filegroup(incr)
        self._read_data(nav,sep)
        self._compute_var()
        
    def _find_filegroup(self,incr):
        path = os.path.dirname(self.filename)
        file = os.path.basename(self.filename)
        m = P.search(file)
        tail = m.group(3)
        flag = m.group(1)
        otime=m.group(2)
        otime = dateparser.parse('20%s/%s/%s-%s:00:00' % (otime[:2],otime[2:4],otime[4:6],otime[6:8]))
        otime_b = otime - datetime.timedelta(hours=incr)
        otime_a = otime + datetime.timedelta(hours=incr)
        self.filename_b = path+os.sep+flag+otime_b.strftime('%y%m%d%H')+tail
        self.filename_a = path+os.sep+flag+otime_a.strftime('%y%m%d%H')+tail
        
    def _read_data(self,nav,sep):
        data = pd.read_csv(self.filename,sep=sep,na_values=nav,index_col='station_id')
        if os.path.isfile(self.filename_b):
            data_b = pd.read_csv(self.filename_b,sep=sep,na_values=nav,index_col='station_id')
        else:
            data_b = data.copy()
        if os.path.isfile(self.filename_a):
            data_a = pd.read_csv(self.filename_a,sep=sep,na_values=nav,index_col='station_id')
        else:
            data_a = data.copy()
        data_a.columns=data_a.columns.map(lambda x : x[:]+'_a')
        data_b.columns=data_b.columns.map(lambda x : x[:]+'_b')    
        df = pd.concat([data,data_b,data_a],axis=1)
        df=df[:][pd.notnull(df['longitude'])]
        need_to_drop=[]
        for col in list(df):
            if col.endswith('_a') or col.endswith('_b'):
                need_to_drop.append(col)
                continue
            df_ab = df.copy()
            missing_vals = pd.isnull(df[col])
            df[col][missing_vals] = df_ab[col+'_b'][missing_vals]
            missing_vals = pd.isnull(df[col])
            df[col][missing_vals] = df_ab[col+'_a'][missing_vals]
        need_to_drop.append('rain_6')
        need_to_drop.append('rain_24')
        self.df = df.drop(need_to_drop,axis=1)
        
    def _compute_var(self):
        geometry = [Point(xy) for xy in zip(self.df.longitude,self.df.latitude)]
        crs = {'init':'epsg:4326'}
        data = gpd.GeoDataFrame(self.df,crs=crs,geometry=geometry)
        GUANGDONG.crs = data.crs
        try:
            data_guangdong = gpd.sjoin(data,GUANGDONG,how='inner')
            self.mean = data_guangdong.mean()
        except:
            pass

