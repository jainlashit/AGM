#pragma once

#include <agm_model.h>
#include <agm_modelException.h>

#if ROBOCOMP_SUPPORT == 1
	#include <AGMAgent.h>
	using namespace RoboCompAGMAgent;
#endif

/*! Converts an STD string to float. */
float str2float(const std::string &s);
/*! Converts an STD string to integer. */
int32_t str2int(const std::string &s);


/*! Converts a float to an STD string. */
std::string float2str(const float &f);
/*! Converts an integer to an STD string. */
std::string int2str(const int32_t &i);



#if ROBOCOMP_SUPPORT == 1

/*!
 * \class AGMMisc
 * @brief Class containing several useful functions.
 *
 * Class containing several useful functions.
 * 
 */
class AGMMisc
{
public:
	/*! Publish a new world model (<em>worldModel</em>) using the proxy <em>agmagenttopic</em> using <em>oldModel</em> as the old model. */
	static void publishModification(AGMModel::SPtr &newModel, AGMAgentTopicPrx &agmagenttopic, AGMModel::SPtr &oldModel);
	static inline float str2float(const std::string &s) {  ::str2float(s); }
	static inline int32_t str2int(const std::string &s) {  ::str2int(s); }
	static inline std::string str2float(const float &f) {  ::float2str(f); }
	static inline std::string str2int(const int32_t &i) {  ::int2str(f); }
}

#endif
