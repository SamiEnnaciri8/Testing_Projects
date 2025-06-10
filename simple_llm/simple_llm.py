from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
import yaml
from langchain_ollama import ChatOllama


#firstly open the config file in order to read which model to use
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)


#call the model from the config file
model = ChatOllama(
    model = config['model_name']
)
#SystemMessage and HumanMessage are used to define the conversation context
messages = [
    SystemMessage(
        "Translate the following text from English to French." 
        "Keep it very concise and do not add any additional information."
    ),
    HumanMessage(
        "Hi!"
    )
]

# system_template = "Translate the following text from English to {language}. " 


# prompt_template = ChatPromptTemplate.from_messages(
#     [("system", system_template), ("user", "{text}")]
# )

# prompt = prompt_template.invoke({"language": "Italian", "text": "hi!"})


response = model.invoke(messages)
print(response.content)