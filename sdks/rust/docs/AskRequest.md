# AskRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**query** | **String** | Natural language question | 
**project** | Option<**String**> | Filter by project (optional) | [optional]
**k** | Option<**i32**> | Number of facts to retrieve | [optional][default to 10]
**temperature** | Option<**f64**> | LLM sampling temperature | [optional][default to 0.3]
**max_tokens** | Option<**i32**> | Max response tokens | [optional][default to 2048]
**system_prompt** | Option<**String**> | Override system prompt (optional) | [optional]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


