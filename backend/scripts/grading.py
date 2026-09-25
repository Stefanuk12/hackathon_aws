from strands import Agent
from strands.models import BedrockModel
import boto3




session = boto3.Session(

)

model = BedrockModel(boto_session=session)

agent = Agent(
    model=model,
    system_prompt=("You are the judge of a game."
                   "You will be given both the name of an AWS service and a description of it."
                   "You have to give the user a concise score out of 10 of how close they are."
                   "You are to answer in plain ASCII. Keep the output to a few sentences.")
)


#user_input = (service_name,",", user_answer)


response = agent("Bedrock, A stone you can sleep on")

print(response)

