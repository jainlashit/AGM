#ifndef WORLDMODELEDGE_H
#define WORLDMODELEDGE_H

#include <string>

#include <stdint.h>

#include "worldModel.h"

class WorldModelEdge
{
public:
	WorldModelEdge();
	~WorldModelEdge();
	WorldModelEdge(int32_t a, int32_t b, std::string linking_);
	WorldModelEdge(const WorldModelEdge &src);
	WorldModelEdge& operator=(const WorldModelEdge &src);

	std::string getLabel() const;
	std::pair<int32_t, int32_t> getSymbolPair() const;

	void setLabel(std::string l);
	void setSymbolPair(std::pair<int32_t, int32_t> p);

	std::string toString(const WorldModel::SPtr &world) const;
	std::string toString(const WorldModel *world) const;

	void getStrings(const WorldModel::SPtr &world, std::string &label, std::string &a, std::string &b) const;
	void getStrings(const WorldModel *world, std::string &label, std::string &a, std::string &b) const;

// protected:
	std::string linking;
	std::pair<int32_t, int32_t> symbolPair;
private:
	void setFrom(const WorldModelEdge &src);
};

#endif