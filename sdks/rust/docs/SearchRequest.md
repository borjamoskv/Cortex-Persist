# SearchRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**query** | **String** | Natural language search query | 
**k** | Option<**i32**> | Number of results | [optional][default to 5]
**project** | Option<**String**> | Filter by project | [optional]
**as_of** | Option<**String**> | Temporal filter (ISO 8601) | [optional]
**fact_type** | Option<**String**> | Filter by fact type | [optional]
**tags** | Option<**Vec<String>**> | Filter by tags | [optional]
**graph_depth** | Option<**i32**> | Enable Graph-RAG (0=off, >0=depth of context traversal) | [optional][default to 0]
**include_graph** | Option<**bool**> | Include the localized context subgraph in response | [optional][default to false]

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


