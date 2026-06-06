# SearchRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Query** | **string** | Natural language search query | 
**K** | Pointer to **int32** | Number of results | [optional] [default to 5]
**Project** | Pointer to **NullableString** | Filter by project | [optional] 
**AsOf** | Pointer to **NullableString** | Temporal filter (ISO 8601) | [optional] 
**FactType** | Pointer to **NullableString** | Filter by fact type | [optional] 
**Tags** | Pointer to **[]string** | Filter by tags | [optional] 
**GraphDepth** | Pointer to **int32** | Enable Graph-RAG (0&#x3D;off, &gt;0&#x3D;depth of context traversal) | [optional] [default to 0]
**IncludeGraph** | Pointer to **bool** | Include the localized context subgraph in response | [optional] [default to false]

## Methods

### NewSearchRequest

`func NewSearchRequest(query string, ) *SearchRequest`

NewSearchRequest instantiates a new SearchRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSearchRequestWithDefaults

`func NewSearchRequestWithDefaults() *SearchRequest`

NewSearchRequestWithDefaults instantiates a new SearchRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetQuery

`func (o *SearchRequest) GetQuery() string`

GetQuery returns the Query field if non-nil, zero value otherwise.

### GetQueryOk

`func (o *SearchRequest) GetQueryOk() (*string, bool)`

GetQueryOk returns a tuple with the Query field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetQuery

`func (o *SearchRequest) SetQuery(v string)`

SetQuery sets Query field to given value.


### GetK

`func (o *SearchRequest) GetK() int32`

GetK returns the K field if non-nil, zero value otherwise.

### GetKOk

`func (o *SearchRequest) GetKOk() (*int32, bool)`

GetKOk returns a tuple with the K field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetK

`func (o *SearchRequest) SetK(v int32)`

SetK sets K field to given value.

### HasK

`func (o *SearchRequest) HasK() bool`

HasK returns a boolean if a field has been set.

### GetProject

`func (o *SearchRequest) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *SearchRequest) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *SearchRequest) SetProject(v string)`

SetProject sets Project field to given value.

### HasProject

`func (o *SearchRequest) HasProject() bool`

HasProject returns a boolean if a field has been set.

### SetProjectNil

`func (o *SearchRequest) SetProjectNil(b bool)`

 SetProjectNil sets the value for Project to be an explicit nil

### UnsetProject
`func (o *SearchRequest) UnsetProject()`

UnsetProject ensures that no value is present for Project, not even an explicit nil
### GetAsOf

`func (o *SearchRequest) GetAsOf() string`

GetAsOf returns the AsOf field if non-nil, zero value otherwise.

### GetAsOfOk

`func (o *SearchRequest) GetAsOfOk() (*string, bool)`

GetAsOfOk returns a tuple with the AsOf field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAsOf

`func (o *SearchRequest) SetAsOf(v string)`

SetAsOf sets AsOf field to given value.

### HasAsOf

`func (o *SearchRequest) HasAsOf() bool`

HasAsOf returns a boolean if a field has been set.

### SetAsOfNil

`func (o *SearchRequest) SetAsOfNil(b bool)`

 SetAsOfNil sets the value for AsOf to be an explicit nil

### UnsetAsOf
`func (o *SearchRequest) UnsetAsOf()`

UnsetAsOf ensures that no value is present for AsOf, not even an explicit nil
### GetFactType

`func (o *SearchRequest) GetFactType() string`

GetFactType returns the FactType field if non-nil, zero value otherwise.

### GetFactTypeOk

`func (o *SearchRequest) GetFactTypeOk() (*string, bool)`

GetFactTypeOk returns a tuple with the FactType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFactType

`func (o *SearchRequest) SetFactType(v string)`

SetFactType sets FactType field to given value.

### HasFactType

`func (o *SearchRequest) HasFactType() bool`

HasFactType returns a boolean if a field has been set.

### SetFactTypeNil

`func (o *SearchRequest) SetFactTypeNil(b bool)`

 SetFactTypeNil sets the value for FactType to be an explicit nil

### UnsetFactType
`func (o *SearchRequest) UnsetFactType()`

UnsetFactType ensures that no value is present for FactType, not even an explicit nil
### GetTags

`func (o *SearchRequest) GetTags() []string`

GetTags returns the Tags field if non-nil, zero value otherwise.

### GetTagsOk

`func (o *SearchRequest) GetTagsOk() (*[]string, bool)`

GetTagsOk returns a tuple with the Tags field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTags

`func (o *SearchRequest) SetTags(v []string)`

SetTags sets Tags field to given value.

### HasTags

`func (o *SearchRequest) HasTags() bool`

HasTags returns a boolean if a field has been set.

### SetTagsNil

`func (o *SearchRequest) SetTagsNil(b bool)`

 SetTagsNil sets the value for Tags to be an explicit nil

### UnsetTags
`func (o *SearchRequest) UnsetTags()`

UnsetTags ensures that no value is present for Tags, not even an explicit nil
### GetGraphDepth

`func (o *SearchRequest) GetGraphDepth() int32`

GetGraphDepth returns the GraphDepth field if non-nil, zero value otherwise.

### GetGraphDepthOk

`func (o *SearchRequest) GetGraphDepthOk() (*int32, bool)`

GetGraphDepthOk returns a tuple with the GraphDepth field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetGraphDepth

`func (o *SearchRequest) SetGraphDepth(v int32)`

SetGraphDepth sets GraphDepth field to given value.

### HasGraphDepth

`func (o *SearchRequest) HasGraphDepth() bool`

HasGraphDepth returns a boolean if a field has been set.

### GetIncludeGraph

`func (o *SearchRequest) GetIncludeGraph() bool`

GetIncludeGraph returns the IncludeGraph field if non-nil, zero value otherwise.

### GetIncludeGraphOk

`func (o *SearchRequest) GetIncludeGraphOk() (*bool, bool)`

GetIncludeGraphOk returns a tuple with the IncludeGraph field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIncludeGraph

`func (o *SearchRequest) SetIncludeGraph(v bool)`

SetIncludeGraph sets IncludeGraph field to given value.

### HasIncludeGraph

`func (o *SearchRequest) HasIncludeGraph() bool`

HasIncludeGraph returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


