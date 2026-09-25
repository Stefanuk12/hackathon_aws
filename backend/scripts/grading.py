from strands import Agent
from strands.models import BedrockModel
import boto3




session = boto3.Session(
    aws_access_key_id="ASIAZGW2IH475DPHUPHP",
    aws_secret_access_key="Jt5WkP9gH7DeuEfTV0Xzy9b+spKzt7KZaUQitH7F",
    aws_session_token="IQoJb3JpZ2luX2VjECUaCXVzLWVhc3QtMSJHMEUCIBK6jiHurF5z5Mqi07JEUhVUqWqTxv9Dhn957OMbn/0WAiEA7Fgcw/Z5BXE+MlkSQb+Z+agaoxPq/yyXt862mZz/cLEqogII7v//////////ARABGgw2MzI4OTE2NTM5NTEiDCICLo+4pXWFvPTEeCr2Ac+l6x4KcYfnVAUMA2Hva+/7Nnv2g+qxztekbG31beNyU2RmxRCQQDyEMsDK8VaYwSbVFbLaDutSFsZKbhL6I115FalMhC80y2OuANsHIN+5ycZdvfNfrpiIcuOBuTKveMCsyd3gD9AGn3CjRjFyCGgfhm4M5joYpna2U3BaJrdIlU3f+qLSKypwekkSIkUJ5et/qZ9bj/3gN8Gaz/s8cmPLtmb47bFRrYklijIRL1hDjv1zfwyXhtnNdNTF5HktKpm0SFeNJ3GTBnh4xosOMHoFnTYONG+6IzTMTrP+mLRm02XEd1F1e8Cyza9rciMkeWdRugvZdTD7z9nVBjqdAQP98vLWvi+GbRyRnqrLfrSwGdJ3rU3FgObnfRAi1PzsfqYd+j7PSgWk2rCIqLdfs+u5ZNvZ6rOx8WSphehSY0bJs5R7hp/Y0JX2QbGNCreQenMSfdVKBmY9IoqU2+hb48gXijQ3vfO0fU5LzP6pceAoxQyAwzH48P5GhIAsHTrUG0u/6+OofSkSeUSHEnlX/16VRVXURqujgl8jMEM=",
    region_name="us-east-1",
)

model = BedrockModel(boto_session=session)

agent = Agent(
    model=model,
    system_prompt=("You are the judge of a game. You will be given both the name of an AWS service and a description of it. You have to give the user a concise score out of 10 of how close they are. You are to answer in plain ASCII")
)


user_input = (service_name,user_answer)


response = agent(user_input)

print(response)

