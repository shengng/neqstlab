#Parameterspace.py 
#Defines classes and functions to span and traverse a parameter space in the qtlab environment.


from pylab import *
from time import time,sleep
import os
import qt

curve = np.zeros((0,2))
# curve = np.mat(curve.copy())
def hilbert(x0, y0, xi, xj, yi, yj, n):
    if n <= 0:
        X = x0 + (xi + yi)/2
        Y = y0 + (xj + yj)/2
        
        # Output the coordinates of the cv
        global curve
        #curve=np.append(curve, [[X,Y]],axis=0)
        curve=np.vstack((curve,(X,Y)))
        #print '%s %s 0' % (X, Y)
    else:
        hilbert(x0,               y0,               yi/2, yj/2, xi/2, xj/2, n - 1)
        hilbert(x0 + xi/2,        y0 + xj/2,        xi/2, xj/2, yi/2, yj/2, n - 1)
        hilbert(x0 + xi/2 + yi/2, y0 + xj/2 + yj/2, xi/2, xj/2, yi/2, yj/2, n - 1)
        hilbert(x0 + xi/2 + yi,   y0 + xj/2 + yj,  -yi/2,-yj/2,-xi/2,-xj/2, n - 1)

def param_hilb(xs, n=5,**lopts):
	hilbert(xs[0].begin, xs[1].begin, xs[0].end-xs[0].begin, 0,0, xs[1].end-xs[1].begin, n)
	return curve

def sweep_func_helper(xs, **lopts):
	z = np.array([])
	x = xs[0]
	u = np.arange(x.begin,x.end,x.stepsize)
	sb_bit = 0
	if len(xs[1:]) > 0:
		for uu in u:
			appendage = sweep_func_helper(xs[1:],**lopts)
			if 'sweepback' in lopts:
				if sb_bit:
					appendage = np.flipud(appendage)
					if 'datablock' in lopts:
						#reverse the flip of the datablock bit#hackyhackyTM
						appendage[:,-1] = np.flipud(appendage[:,-1]) 
					sb_bit = 0
				else:
					sb_bit = 1
			#if  appendage 1d then column stack
			#if len(appendage.shape) == 1:
			z_t = np.column_stack((np.repeat(uu,appendage.shape[0]),appendage))
			if len(z) == 0:
				z = z_t
			else:
				z = np.vstack((z,z_t))
			# else:
				# print appendage.shape
				# z_t = np.concatenate( (np.repeat(uu,appendage.shape[0]),appendage),axis=1)
				# if len(z) == 0:
					# z = z_t
				# else:
					# z = np.vstack((z,z_t))
	else:
		#implement datablock bit
		if 'datablock' in lopts:
			z_t = np.zeros(len(u))
			z_t[-1] = 1
			z = np.column_stack((u,z_t)) 
		else:
			z = u 
	return z

class param(object):
	def __init__(self):
		self.begin = 0
		self.end = 0
		self.instrument = []
		self.instrument_opt = []
		self.module = []
		self.steps = []
		self.stepsize = []
		self.rate_stepsize = []
		self.rate_delay = []
		self.label = ''
		self.unit = 'a.u.'
	
class parspace(object):
	def __init__(self):
		self.xmlfile = ''
		self.xs = [] #empty list of x1,x2 ..xn (param objects)
		self.zs = [] #empty list of parmaham space
		self.measurementname = 'Noname Measurement'
		
	def load_xml(self,filename):
		raise Exception('not implemented yet. Filename: {:<30}'.format(filename))
	
	def add_param(self, param):
		self.xs.append(param)
		
	def add_paramz(self,param):
		self.zs.append(param)
		
	def set_name(self,name):
		self.measurementname = name
	
	def remove_param(self, label='Optional'):
		raise Exception('not implemented yet')
	
	def remove_all_param(self, label='Optional'):	
		self.xs = []
	
	def set_traversefunc(self, func):
		self.traverse_func = func
		
	def data_gen(self):
		trav = self.lineartraverse
		cnt = 0
		while cnt < trav.shape[0]: 
			yield trav[cnt] #yield a single array row including controls bits
			cnt += 1
	
	def traverse(self):
		#traverse the defined parameter space, using e.g. a space filling curve defined in self.traverse_func
		for x in self.xs:
			instr = qt.instruments.get_instruments()[x.instrument]
			instr.set_parameter_rate(x.instrument_opt,x.rate_stepsize,x.rate_delay)
		
		self.lineartraverse = self.traverse_func(self.xs)
		data = qt.Data(name=self.measurementname)

		qt.mstart()
		for i in self.xs:
			data.add_coordinate('{%s} ({%s})' % (i.label,i.unit),
				size=abs((i.end - i.begin) / i.stepsize),
				start=i.begin,
				end=i.end
				)
		for i in self.zs:
			data.add_value('{%s} ({%s})' % (i.label,i.unit))
		
		data.create_file()
        
		plotvaldim =1
		if len(self.xs) > 1:
			plotvaldim = 2
			plot3d = qt.Plot3D(data, name='measure3D', coorddims=(0,1), valdim=2, style='image')
		plot2d = qt.Plot2D(data, name='measure2D', coorddim=0, valdim=plotvaldim, traceofs=10)
		cnt = 0
		for i in self.data_gen():
			try:
				for x in range(len(self.xs)):
					self.xs[x].module(i[x])
			except Exception as e:
				print 'Exception caught: ', e
				
			#t = lambda x,y: sin(x*2*pi)+sin(y*2*pi)
			# if cnt == 0:
				# qt.msleep(4) #wait 4 seconds to start measuring to allow for capacitive effects to dissipate
				# cnt +=1
			r = self.zs[0].module()
			print i
			#another hack
			if len(self.xs) == 1:
				data.add_data_point(i[0],r)
			elif len(self.xs) == 2:
				data.add_data_point(i[0],i[1],r)

			#read out the control bit if it exists..
			try:
				#fixme
				if i[-1] == 1.0:
					data.new_block()
			except Exception as e:
				print e
			qt.msleep(0.001)
			
		data.new_block()
		data.close_file()
		from lib.file_support.spyview import SpyView
		
		qt.mend()
		SpyView(data).write_meta_file()
		print 'measurement ended'	