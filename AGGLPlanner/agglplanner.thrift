struct PlanningResults
{
	1: i32 cost;
	2: string plan;
}

service AGGLPlanner
{
	i32 getDomainIdentifier(1:string domainText);
	i32 getTargetIdentifier(1:string targetText);
	PlanningResults planAGGT(1: i32 domainId, 2: string initWorld, 3:i32 targetId, 4: list<string> excludeList, 5: list<string> awakenRules);
}
