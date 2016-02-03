import sys, traceback, Ice, subprocess, threading, time, Queue, os, time
import IceStorm

# AGM
sys.path.append('/usr/local/share/agm')

from parseAGGL import *
from generateAGGLPlannerCode import *
from agglplanner import *
from agglplanchecker import *
from agglplanningcache import *

import xmlModelParser

import pickle

# Check that RoboComp has been correctly detected
ROBOCOMP = ''
try:
	ROBOCOMP = os.environ['ROBOCOMP']
except:
	pass
if len(ROBOCOMP)<1:
	print 'ROBOCOMP environment variable not set! Exiting.'
	sys.exit()
preStr = "-I"+ROBOCOMP+"/interfaces/ --all "+ROBOCOMP+"/interfaces/"
Ice.loadSlice(preStr+"AGMCommonBehavior2.ice")
Ice.loadSlice(preStr+"AGMExecutive2.ice")
Ice.loadSlice(preStr+"AGMWorldModel2.ice")
Ice.loadSlice(preStr+"Speech.ice")
Ice.loadSlice(preStr+"Planning.ice")
import RoboCompAGMCommonBehavior
import RoboCompAGMExecutive
import RoboCompAGMWorldModel
import RoboCompSpeech
import RoboCompPlanning

import AGMModelConversion

#ret, stepsFwd, planMonitoring =
def AGMExecutiveMonitoring(domainClass, domainPath, init, currentModel, target, plan, stepsFwd=0):
	try:
		currentPlan = AGGLPlannerPlan(plan)
	except:
		traceback.print_exc()
		sys.exit(134)

	try:
		ret2 = False
		if len(currentPlan)>0:
			try:
				#print 'Trying one step ahead...', stepsFwd
				newPlan = currentPlan.removeFirstAction(currentModel)
				ret2, stepsFwd2, planMonitoring2 = AGMExecutiveMonitoring(domainClass, domainPath, init, currentModel, target, newPlan, stepsFwd+1)
			except:
				print steps, 'steps ahead did not work'
				traceback.print_exc()
				ret2 = False
		if ret2:
			print 'ok', stepsFwd
			return ret2, stepsFwd2, planMonitoring2
		else:
			try:
				#print 'CHECK with a plan of', len(plan), 'steps,', stepsFwd, 'forward'
				#print plan
				p = PyPlanChecker(domainClass, domainPath, init, currentPlan, target, '', verbose=False)
				if p.valid:
					#print 'GOT PLAN FROM MONITORING!!!'
					#print currentPlan
					return True, stepsFwd, currentPlan
				else:
					#print 'doesn\'t work'
					return False, 0, None
			except:
				traceback.print_exc()
				return False, 0, None
	except:
		traceback.print_exc()
		sys.exit(4991)
	traceback.print_exc()
	sys.exit(692)



class Executive(object):
	def __init__(self, agglPath, initialModelPath, initialMissionPath, executiveTopic, executiveVisualizationTopic, speech):
		self.executiveActive = True
		self.modelMutex = threading.RLock()
		self.mutex = threading.RLock()
		self.pypyKillMutex = threading.RLock()
		self.pypyInProgress = 0
		self.plannerExecutionID=0
		self.agents = dict()
		self.plan = None
		self.modifications = 0
		self.lastPypyKill = time.time()
		self.cache = PlanningCache()

		# Set proxies
		self.executiveTopic = executiveTopic
		self.executiveVisualizationTopic = executiveVisualizationTopic
		self.speech = speech

		self.agglPath = agglPath
		self.agmData = AGMFileDataParsing.fromFile(self.agglPath)
		self.agmData.generateAGGLPlannerCode("/tmp/domainActive.py", skipPassiveRules=False)
		self.agmData.generateAGGLPlannerCode("/tmp/domainPasive.py", skipPassiveRules=True)
		self.initialModelPath = initialModelPath
		self.initialModel = xmlModelParser.graphFromXML(initialModelPath)
		self.lastModification = self.initialModel
		self.backModelICE  = None
		self.setAndBroadcastModel(xmlModelParser.graphFromXML(initialModelPath))
		self.worldModelICE = AGMModelConversion.fromInternalToIce(self.currentModel)
		self.setMission(initialMissionPath, avoidUpdate=True)

	#########################################################################
	#                                                                     ###
	# E X E C U T I V E   I N T E R F A C E   I M P L E M E N T A T I O N ###
	#                                                                     ###
	#                         b e g i n s   h e r e                       ###
	#                                                                     ###
	#########################################################################
	def activate(self):
		self.executiveActive = True

	def deactivate(self):
		self.executiveActive = False

	def structuralChangeProposal(self, worldModelICE, sender, log):
		#
		#  H E R E     W E     S H O U L D     C H E C K     T H E     M O D I F I C A T I O N     I S     V A L I D
		#

		# Get structuralChange mutex
		if self.modelMutex.acquire(blocking=False) == False:
			return ProposalError.Locked
		try:
			# Ignore outdated modifications
			if worldModelICE.version != self.lastModification.version+1:
				return ProposalError.OldModel

			# Here we're OK with the modification, accept it, but first check if replanning is necessary
			internalModel = AGMModelConversion.fromIceToInternal_model(worldModelICE, ignoreInvalidEdges=True) # set internal model
			try:                                                                                               # is replanning necessary?
				avoidReplanning = False
				if internalModel.equivalent(self.lastModification):
					avoidReplanning = True
			except AttributeError:
				pass
			self.lastModification = internalModel                                                              # store last modification
			self.modifications++
			self.worldModelICE = worldModelICE
			# Store the model in XML
			try:
				internalModel.toXML('modification'+(str(self.modifications).zfill(4))+'.xml')
			except:
				print 'There was some problem updating internal model to xml'
			# Set and broadst the model
			try:
				self.setAndBroadcastModel(internalModel)
			except:
				print 'There was some problem broadcasting the model'
				sys.exit(-1)
			# Force replanning
			try:
				if not avoidReplanning:
					self.updatePlan()
			except:
				print 'There was some problem updating internal model to xml'
		finally:
			self.modelMutex.release()


	def symbolUpdate(self, nodeModification):
		self.symbolsUpdate([nodeModification])


	def symbolsUpdate(self, symbols):
		try:
			self.modelMutex.acquire()
			try:
				for symbol in symbols:
					internal = AGMModelConversion.fromIceToInternal_node(symbol)
					self.currentModel.nodes[internal.name] = copy.deepcopy(internal)
			except:
				print 'There was some problem with update node'
				sys.exit(1)
			self.executiveTopic.symbolsUpdated(symbols)
		finally:
			self.modelMutex.release()


	def edgeUpdate(self, edge):
		self.edgesUpdate([edge])

	def edgesUpdate(self, edges)
		try:
			self.modelMutex.acquire()
			for edge in edges:
				internal = AGMModelConversion.fromIceToInternal_edge(edge)
				found = False
				for i in xrange(len(self.currentModel.links)):
					if str(self.currentModel.links[i].a) == str(edge.a):
						if str(self.currentModel.links[i].b) == str(edge.b):
							if str(self.currentModel.links[i].linkType) == str(edge.edgeType):
								self.currentModel.links[i].attributes = copy.deepcopy(edge.attributes)
								self.executiveTopic.edgeUpdated(edge)
								found = True
				if not found:
					print 'couldn\'t update edge because no match was found'
					print 'edge', edge.a, edge.b, edge.edgeType
		finally:
			self.mutex.release()


	def setMission(self, target, avoidUpdate=False):
		self.mutex.acquire( )
		self.targetStr = target
		try:
			temp = AGMFileDataParsing.targetFromFile(target)
			self.target = generateTarget_AGGT(temp)
			ofile = open("/tmp/target.py", 'w')
			ofile.write(self.target)
			ofile.close()
			if not avoidUpdate:
				print 'do update plan'
				self.updatePlan()
		except:
			print 'There was some problem setting the mission'
			sys.exit(1)
		self.mutex.release()



	def getModel(self):
		return self.worldModelICE


	def getNode(self, identifier):
		for n in self.worldModelICE.nodes:
			if n.nodeIdentifier == identifier:
				return n


	def getEdge(self, srcIdentifier, dstIdentifier, label):
		for e in self.worldModelICE.edges:
			if e.a == srcIdentifier and e.b == dstIdentifier and e.edgeType == label:
				return e


	def getData(self):
		return self.worldModelICE, self.targetStr, self.plan)


	def broadcastPlan(self):
		self.mutex.acquire( )
		try:
			self.publishExecutiveVisualizationTopic()
			self.sendParams()
		except:
			print 'There was some problem broadcasting the plan'
			sys.exit(1)
		self.mutex.release()

	def broadcastModel(self):
		self.mutex.acquire( )
		try:
			print '<<<broadcastinnn'
			print self.currentModel.filterGeometricSymbols()
			self.executiveTopic.structuralChange(AGMModelConversion.fromInternalToIce(self.currentModel))
			print 'broadcastinnn>>>'
		except:
			print traceback.print_exc()
			print 'There was some problem broadcasting the model'
			sys.exit(1)
		self.mutex.release()
	#########################################################################
	#                                                                     ###
	# E X E C U T I V E   I N T E R F A C E   I M P L E M E N T A T I O N ###
	#                                                                     ###
	#                            e n d s    h e r e                       ###
	#                                                                     ###
	#########################################################################



	def setAgent(self, name, proxy):
		self.agents[name] = proxy


	def setAndBroadcastModel(self, model):
		#print model
		self.currentModel = model
		self.broadcastModel()

	def ignoreCommentsInPlan(self, plan):
		ret = []
		for i in plan:
			if len(i) > 0:
				if i[0] != '#':
					ret.append(i)
		return ret

	def callMonitoring(self, peid):
		stored = False
		stepsFwd = 0
		print 'Trying with the last steps of the current plan...'
		domainPath = '/tmp/domainActive.py'
		init   = '/tmp/lastWorld'+peid+'.xml'
		target = '/tmp/target.py'
		try:
			#print '<<<Call Monitoring'
			#print '<<<Call Monitoring'
			#print self.plan
			#print '   Call Monitoring>>>'
			#print '   Call Monitoring>>>'
			#print 'aa', type(self.plan), self.plan
			#try:
				#os.system("rm -rf " + peid)
				#os.system("mkdir " + peid)
				#h = open(peid+'/agmData.pckl', 'w')
				#print type(h)
				#pickle.dump(self.agmData,      h)

				#h = open(peid+'/domainPath.pckl', 'w')
				#print type(h)
				#pickle.dump(domainPath,        h)

				#h = open(peid+'/domainPath.pckl', 'w')
				#print type(h)
				#pickle.dump(init,              h)

				#h = open(peid+'/currentModel.pckl', 'w')
				#print type(h)
				#pickle.dump(self.currentModel, h)

				#h = open(peid+'/plan.pckl', 'w')
				#print type(h)
				#pickle.dump(self.plan,         h)
			#except:
				#pass

			ret, stepsFwd, planMonitoring = AGMExecutiveMonitoring(self.agmData, domainPath, init, self.currentModel.filterGeometricSymbols(), target, AGGLPlannerPlan(self.plan))
			#print 'bb'
			#print ret, stepsFwd, planMonitoring
			if ret:
				print 'Using a ', stepsFwd, 'step forwarded version of the previous plan'
				stored = True
				self.plan = planMonitoring
			else:
				print 'No modified version of the current plan satisfies the goal. Replanning is necessary.'
				stored = False
		except:
			print traceback.print_exc()
			print 'It didn\'t seem to work.'
			stored = False
		print 'done callMonitoring', stored, stepsFwd
		return stored, stepsFwd

	def updatePlan(self):
		# Kill any previous planning process
		while self.mutex.acquire(0)==False:
			now = time.time()
			elap = (now - self.lastPypyKill)
			print 'couldn\'t acquire', elap
			if elap > 3.:
				try:
					subprocess.call(["killall", "-9", "pypy"])
				except:
					pass
				self.lastPypyKill = now
			time.sleep(1)
		self.mutex.release()


		# First, try with the current plan
		stored = False
		if self.plan != None and False:
			self.pypyKillMutex.acquire()
			try:
				peid = '_'+str(self.plannerExecutionID)
			except:
				print 'There was some problem broadcasting the model'
				sys.exit(1)
			self.pypyKillMutex.release()
			stored, stepsFwd = self.callMonitoring(peid)
			print stored, stepsFwd
		else:
			print 'There was no previous plan'

		print 'Running the planner?', stored==False
		if stored == False:
			# Run planner
			start = time.time()
			#PRE
			self.pypyKillMutex.acquire()
			try:
				self.pypyInProgress += 1
				self.plannerExecutionID+=1
				peid = '_'+str(self.plannerExecutionID)
				self.currentModel.filterGeometricSymbols().toXML("/tmp/lastWorld"+peid+".xml")
			except:
				print 'There was some problem writing the model to an XML:', "/tmp/lastWorld"+peid+".xml"
				sys.exit(1)
			self.pypyKillMutex.release()
			# CALL
			argsss = ["agglplanner", self.agglPath, "/tmp/domainActive.py", "/tmp/lastWorld"+peid+".xml", "/tmp/target.py", "/tmp/result"+peid+".txt"]
			print 'Ask cache'
			cacheResult = self.cache.getPlanFromFiles(argsss[2], argsss[3], argsss[4])
			if cacheResult:
				print 'Got plan from cache'
				print '<<<'
				print cacheResult[1]
				print '>>>'
				cacheSuccess = cacheResult[0]
				cachePlan = cacheResult[1]
				lines = cacheResult[1].split('\n')
			else:
				print 'Running the planner...'
				try:
					print argsss
					subprocess.call(argsss)
				except:
					pass
				#POST Check if the planner was killed
				print 'pkm2'
				self.pypyKillMutex.acquire()
				try:
					self.pypyInProgress -= 1
					if self.pypyInProgress == 0:
						plannerWasKilled = False
					else:
						plannerWasKilled = True
				except:
					print 'There was some problem doing this'
					sys.exit(1)
				self.pypyKillMutex.release()
				#CONTINUE?                       Probably i'ts better just to try to open the file and consider it was killed if there's no result file...
				#if plannerWasKilled:
					#print 'There\'s another planning process running... abort'
					#return
				end = time.time()
				print 'It took', end - start, 'seconds'
				print 'includeFromFiles: ', argsss[2], argsss[3], argsss[4], "/tmp/result"+peid+".txt", True
				self.cache.includeFromFiles(argsss[2], argsss[3], argsss[4], "/tmp/result"+peid+".txt", True)
				ofile = open("/tmp/result"+peid+".txt", 'r')
				lines = self.ignoreCommentsInPlan(ofile.readlines())
				ofile.close()
			# Get the output
			try:
				self.plan = AGGLPlannerPlan('\n'.join(lines), planFromText=True)
				stored, stepsFwd = self.callMonitoring(peid)
			except: # The planner was probably killed
				traceback.print_exc()
				return
		else:
			print 'Got plan from monitorization'
			print self.plan
			print 'Got plan from monitorization'

		# Extract first action
		action = "none"
		parameterMap = dict()
		if len(self.plan) > 0:
			action = self.plan.data[0].name
			parameterMap = self.plan.data[0].parameters

		print 'action: <'+action+'>  parameters:  <'+str(parameterMap)+'>'
		# Prepare parameters
		params = dict()
		params['action'] = RoboCompAGMCommonBehavior.Parameter()
		params['action'].editable = False
		params['action'].value = action
		params['action'].type = 'string'
		params['plan'] = RoboCompAGMCommonBehavior.Parameter()
		params['plan'].editable = False
		params['plan'].value = str(self.plan)
		params['plan'].type = 'string'
		for p in parameterMap.keys():
			params[p] = RoboCompAGMCommonBehavior.Parameter()
			params[p].editable = False
			params[p].value = parameterMap[p]
			params[p].type = 'string'
		# Send plan
		self.lastParamsSent = copy.deepcopy(params)
		self.sendParams()
		# Publish new information using the executiveVisualizationTopic
		self.publishExecutiveVisualizationTopic()
		print 'done'

	#
	#
	def publishExecutiveVisualizationTopic(self):
		try:
			print self.plan
			planPDDL = RoboCompPlanning.Plan() # Generate a PDDL-like version of the current plan for visualization
			planPDDL.cost = -2.
			try:
				planPDDL.cost = -1.
				planPDDL.actions = []
				for step in self.plan:
					action = RoboCompPlanning.Action()
					action.name = step.name
					action.symbols = str(step.parameters).translate(None, '{}').split(',')
					planPDDL.actions.append(action)
			except:
				traceback.print_exc()
				print 'Error generating PDDL-like version of the current plan'
			#self.executiveVisualizationTopic.update(self.worldModelICE, AGMModelConversion.fromInternalToIce(self.target), planPDDL)
		except:
			traceback.print_exc()
			print "can't publish executiveVisualizationTopic.update"

	#
	#
	def sendParams(self):
		print 'Send plan to'
		for agent in self.agents:
			print '\t', agent,
			try:
				self.agents[agent].activateAgent(self.lastParamsSent)
			except:
				print '     (can\'t connect to', agent, '!!!)',
			print ''

