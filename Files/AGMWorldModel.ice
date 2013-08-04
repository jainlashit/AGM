#ifndef ROBOCOMPAGMWORLDMODELICE_H
#define ROBOCOMPAGMWORLDMODELICE_H

module RoboCompAGMWorldModel
{
	dictionary<string, string> StringDictionary;
	enum BehaviorResultType { InitialWorld, BehaviorBasedModification, BehaviorBasedNumericUpdate, StatusFailTimeout, StatusFailOther, StatusActive, StatusIdle };

	struct Node
	{
		string nodeType;
		int nodeIdentifier;
		StringDictionary attributes;
	};
	sequence<Node> NodeSequence;

	struct Edge
	{
		int a;
		int b;
		string edgeType;
	};
	sequence<Edge> EdgeSequence;

	struct World
	{
		NodeSequence nodes;
		EdgeSequence edges;
	};

	struct ModelEvent
	{
		string sender;
		BehaviorResultType why;
		World backModel;
		World newModel;
	};

};

#endif
