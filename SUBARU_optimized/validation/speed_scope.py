"""Scope guards for the replacement of generated scalar formatting nodes."""
import re
PROMPTS={'setVariable_priorityGuideFixed','setVariable_priorityPrompt','answer_priority'}
def retired(ident):
 return ident in {'conditionGroup_priorityFormatRetry','setVariable_priorityFormatRetryIncrement','goto_priorityFormatRetry'} or re.fullmatch(r'setVariable_item(?:Priority|Status|Reason|Bucket|Incomplete|Link|LinkReason)P\d+(?:High|Medium|Low)?',ident)is not None

def strip_formatting(x):
 if isinstance(x,list):
  return [strip_formatting(v)for v in x if not(isinstance(v,dict)and(v.get('id','').startswith(('setVariable_item','setVariable_priorityFormat','conditionGroup_priorityFormat'))or v.get('id')in {'setVariable_priorityGateSnapshot','setVariable_priorityFailedSnapshot','setVariable_priorityWaitSnapshot','setVariable_priorityPreviousResultInit','setVariable_priorityPreviousCheckInit','setVariable_priorityBeforeAISnapshot','setVariable_priorityAfterAISnapshot','setVariable_priorityBeforeSaveSnapshot','setVariable_priorityAfterSaveSnapshot','conditionGroup_itemEmergencyInvalid'}))]
 if isinstance(x,dict):
  return {k:strip_formatting(v)for k,v in x.items()if not((x.get('id')in PROMPTS-{'answer_priority'}and k=='value')or(x.get('id')=='answer_priority'and k in {'additionalInstructions','userInput'}))}
 return x
