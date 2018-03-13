
# coding: utf-8

# In[3]:


import pandas as pd    # <---python 的通用类似数据库的数据存储模块，可以轻松的实现各种分析或与其他模块的对接。
import numpy as np     # <---这个模块就厉害了！可以说是python所有数组或矩阵计算的基础模块
                       #，擅长处理各种各样的数据类型，还能以object形式组建数组。
import dateparser      # <---网上查找到的处理时间信息的模块，据作者说基本可以将世界各国语言写成的人类能读懂的时间信息转化成
                       # python中的datetime类型对象，实现进一步处理。
import datetime        # <---时间类对象的本体模块
import re              # <---正则表达式模块，用来快速，精准，高效的处理有规律的文本信息。
import os              # <---跨系统平台的系统命令模块，可以使得python脚本具有跨平台运行的能力。
#以上是本脚本主体部分需要的功能模块。
#from mpl_toolkits.basemap import Basemap 
#import matplotlib.pyplot as plt
#以上是出图以测试数据需要用到的模块。


# In[50]:


NUMBER = '[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?'         #识别一定长度或科学计数法的范例，因经常用到就单独写了
class CTLReader(object):
    def __init__(self,filepath,filename,place_hold=2):
        self.dimensions = {}
        self.variables = {}
        self.ctlpath = filepath
        self.filename = filename
#将ctl文件信息读入一个巨大的字符串中便于之后处理        
        with open(self.ctlpath,'r') as f:
            self.ctl = f.read()
        self._read_data()                #读取二进制文件数据
        self._read_dimensions()          #获取ctl中的维度信息
        self._read_vars(place_hold)      #将二进制文件数据规整为变量明命名的数组
    
    def _read_data(self):        
        self.undef = eval(re.search('undef (%s)' % NUMBER , self.ctl).group(1))    #获取CTL文件中的缺省值信息
        big_endian = bool(re.search('options.*big_endian',self.ctl,flags=re.I))    #探测数据是否是big_endian
        data = np.fromfile(self.filename,'f4')    #以4bytes的浮点形式（单精度）读取二进制文件
        if big_endian:
            data = data.byteswap()    #统一将big_endian数据进行位调换
        self.data = np.ma.masked_values(data,self.undef)    #建立带有默认缺省值的numpy数组并添加到类的自身属性中
        
    def _read_dimensions(self):
        if 'xdef' in self.ctl:    #探测是否存在xdef关键字
            p = re.compile("%s\s+(\d+)\s+linear\s+(%s)\s+(%s)" % ('xdef',NUMBER,NUMBER))    #创建正则维度信息范式
            m = p.search(self.ctl)
            self.variables['longitude'] = np.linspace(float(m.group(2)),
                                                      float(m.group(2))+float(m.group(3))*(int(m.group(1))-1),
                                                      int(m.group(1)))
            self.dimensions['longitude'] = int(m.group(1))
            
        if 'ydef' in self.ctl:    #探测是否存在ydef关键字
            p = re.compile("%s\s+(\d+)\s+linear\s+(%s)\s+(%s)" % ('ydef',NUMBER,NUMBER))    #创建正则维度信息范式
            m = p.search(self.ctl)
            self.variables['latitude'] = np.linspace(float(m.group(2)),
                                                     float(m.group(2))+float(m.group(3))*(int(m.group(1))-1),
                                                     int(m.group(1)))
            self.dimensions['latitude'] = int(m.group(1))
            
        if 'zdef' in self.ctl:    #探测是否存在zdef关键字
            self.variables['levels'] = Variable('levels',self._parse_dimension('zdef'))    #创建“层数”信息变量
            self.dimensions['levels'] = len(self.variables['levels'])
            
        if 'grapes' in self.ctl:  #探测是否存在grapes关键字
            self.variables['time'] = Variable('time',self._parse_dimension('time'))        #创建“时间”信息变量
            #目前只需要处理“单片”时次的数据
            self.dimensions['time'] = 1
            
    def _read_vars(self,place_hold):
        read = False    #是否识别为目标变量的开关

        for line in self.ctl.split('\n'):
            if line.startswith('endvars'):    #探测目标变量组结束符号
                read = False
            if read:
                p = re.compile('(\w+)\s+(\d+)\s+(\d+)\s+(.*)')    #目标变量行的正则范式
                m = p.match(line)
                name = m.group(1)
                var = self.variables[name] = Variable(name)       #生成特定的变量类并在本段方法中以"var"的别名进行描述
                levels = int(m.group(2))
                SPACE = self.dimensions['latitude']*self.dimensions['longitude']
                if levels > 0:
                    var.dimensions = ('time','levels','latitude','longitude')    #当变量为四维数组时变量的维度信息
                    size = self.dimensions['time']*self.dimensions['levels']*(SPACE+place_hold)
                else:
                    var.dimensions = ('time','latitude','longitude')    #当变量为三维数组时变量的维度信息
                    size = self.dimensions['time']*(SPACE+place_hold)
                
                var.shape = tuple(self.dimensions[dim] for dim in var.dimensions)    #根据不同的维度信息创建维度宽度提示元组
                var.data = self.data[i:i+size].reshape(-1,SPACE+place_hold)[:,
                                                                            int(place_hold/2):
                                                                            -int(place_hold/2)].reshape(var.shape)
                #以上操作较复杂，主要就是重构数据，去掉头尾的占位符，再次按照维度重构数据
                i += size    #相当与跳过一定长度的二进制数据字段
                
                units = int(m.group(3))    #单位信息，由于目前阶段处理数据不复杂，暂时不需要添加
                if units != 0:             #变量的量级转化开关（这种功能交给pandas等模拟自动做吧^_^）
                    raise NotImplementedError('for now only 0 units will be implemented!')
                
                var.attributes = {
                    'long_name': m.group(4).strip(),
                    'units': 'not needed right now'
                }
                #以上是变量的描述信息，及单位的存放属性
            if line.startswith('var'):    #探测目标变量组开始符号
                i = 0
                read = True
                
    def _parse_dimension(self,dim):    #用于检索CTL信息中维度相关信息的方法
        
        p = re.compile("%s\s+(\d+)\s+levels([\s\S]+)tdef"  % (dim))    #获取层数的具体信息的正则范式
        m = p.search(self.ctl)
        if m:
            return np.fromstring(m.group(2),sep='\n')    #以换行符分离目标信息，并生成numpy数组
        
        #time info read from file name
        if dim == 'time':    #对时间信息的定制处理
            filetime = os.path.basename(self.filename)
            p = re.compile('mars3km(\d{8})(\d+)')
            m = p.search(filetime)
            date = m.group(1)
            initime = dateparser.parse("20%s %s %s-%s:00:00" % (date[:2],date[2:4],date[4:6],date[6:8]))
            endtime = initime + datetime.timedelta(hours=int(m.group(2)))
            p = re.compile('\s+\d+\s+linear\s+[:\w]+\s+(\d+)(\w{2})')
            m = p.search(self.ctl)
            if m:
                if m.group(2) == 'mn':
                    increment = datetime.timedelta(minutes=int(m.group(1)))
                else:
                    increment = datetime.timedelta(hours=int(m.group(1)))
            return np.array([initime,endtime,increment])
        
    
class Variable(object):    #变量类定义
    def __init__(self,name,data=None):    #创世纪
        self.name = name                  #python说：“要有名字“！于是有了变量
        self.data = data                  #python说：”要有数据“！于是有了变量      
    def __getitem__(self,index):          #python说：”要有方法“！于是有了变量
        return self.data[index]    
    def __getattr__(self,key):
        return self.attributes[key]
    def __len__(self):
        return len(self.data)


# In[51]:


#正式读取数据
#data = CTLReader('./test.ctl','./mars3km17040100001.dat')


# In[5]:


#以下是画图测试用的简单脚本，验证数据并没有读取错误的最后方法就是画出来看！
#%pylab
#仅当你使用jupyter时打开，可以得到一个漂亮的界面化图像操作UI


# In[6]:


#lon,lat = np.meshgrid(np.linspace(96.6,123.3,891),np.linspace(16.6,31.3,491))
#llcrnrlon=lon.min()
#llcrnrlat=lat.min()
#urcrnrlon=lon.max()
#urcrnrlat=lat.max()
#lon_0=(urcrnrlon-llcrnrlon)/2
#lat_0=(urcrnrlat-llcrnrlat)/2
#m=Basemap(lon_0=lon_0,lat_0=lat_0,llcrnrlon=llcrnrlon,llcrnrlat=llcrnrlat,
#              urcrnrlon=urcrnrlon,urcrnrlat=urcrnrlat,resolution='l')
#m.drawcoastlines()
#m.drawcountries()
#m.drawcounties()
##m.readshapefile('./data/XZQ_D','guangdon')
#m.contour(lon,lat,data.variables['cr'][0])


# In[10]:


#print('min',data.variables['cr'][0].min(),'max',data.variables['cr'][0].max())

