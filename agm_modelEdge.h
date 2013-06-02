#ifndef WORLDMODELEDGE_H
#define WORLDMODELEDGE_H

#include <string>

#include <stdint.h>

#include "agm_model.h"

class AGMModelEdge
{
public:
	AGMModelEdge();
	~AGMModelEdge();
	AGMModelEdge(int32_t a, int32_t b, std::string linking_);
	AGMModelEdge(const AGMModelEdge &src);
	AGMModelEdge& operator=(const AGMModelEdge &src);

	std::string getLabel() const;
	std::pair<int32_t, int32_t> getSymbolPair() const;
	void setLabel(std::string l);
	void setSymbolPair(std::pair<int32_t, int32_t> p);

// 	std::string toString(const boost::shared_ptr<AGMModel> &world);
	std::string toString(const AGMModel *world) const;

	
// protected:
	std::string linking;
	std::pair<int32_t, int32_t> symbolPair;
private:
	void setFrom(const AGMModelEdge &src);
};

#endif