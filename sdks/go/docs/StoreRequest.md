# StoreRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Project** | **string** | Project/namespace for the fact | 
**Content** | **string** | The fact content | 
**FactType** | Pointer to **string** | Type: knowledge, decision, mistake, bridge, ghost | [optional] [default to "knowledge"]
**Tags** | Pointer to **[]string** | Optional tags | [optional] 
**Source** | Pointer to **string** | Origin of the fact (e.g. agent:vex) | [optional] [default to ""]
**Confidence** | Pointer to **NullableString** | Optional confidence level (C1-C5) | [optional] 
**Meta** | Pointer to **map[string]interface{}** | Graph-RAG context (subgraph or related entities) | [optional] 

## Methods

### NewStoreRequest

`func NewStoreRequest(project string, content string, ) *StoreRequest`

NewStoreRequest instantiates a new StoreRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewStoreRequestWithDefaults

`func NewStoreRequestWithDefaults() *StoreRequest`

NewStoreRequestWithDefaults instantiates a new StoreRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetProject

`func (o *StoreRequest) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *StoreRequest) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *StoreRequest) SetProject(v string)`

SetProject sets Project field to given value.


### GetContent

`func (o *StoreRequest) GetContent() string`

GetContent returns the Content field if non-nil, zero value otherwise.

### GetContentOk

`func (o *StoreRequest) GetContentOk() (*string, bool)`

GetContentOk returns a tuple with the Content field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetContent

`func (o *StoreRequest) SetContent(v string)`

SetContent sets Content field to given value.


### GetFactType

`func (o *StoreRequest) GetFactType() string`

GetFactType returns the FactType field if non-nil, zero value otherwise.

### GetFactTypeOk

`func (o *StoreRequest) GetFactTypeOk() (*string, bool)`

GetFactTypeOk returns a tuple with the FactType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFactType

`func (o *StoreRequest) SetFactType(v string)`

SetFactType sets FactType field to given value.

### HasFactType

`func (o *StoreRequest) HasFactType() bool`

HasFactType returns a boolean if a field has been set.

### GetTags

`func (o *StoreRequest) GetTags() []string`

GetTags returns the Tags field if non-nil, zero value otherwise.

### GetTagsOk

`func (o *StoreRequest) GetTagsOk() (*[]string, bool)`

GetTagsOk returns a tuple with the Tags field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTags

`func (o *StoreRequest) SetTags(v []string)`

SetTags sets Tags field to given value.

### HasTags

`func (o *StoreRequest) HasTags() bool`

HasTags returns a boolean if a field has been set.

### GetSource

`func (o *StoreRequest) GetSource() string`

GetSource returns the Source field if non-nil, zero value otherwise.

### GetSourceOk

`func (o *StoreRequest) GetSourceOk() (*string, bool)`

GetSourceOk returns a tuple with the Source field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSource

`func (o *StoreRequest) SetSource(v string)`

SetSource sets Source field to given value.

### HasSource

`func (o *StoreRequest) HasSource() bool`

HasSource returns a boolean if a field has been set.

### GetConfidence

`func (o *StoreRequest) GetConfidence() string`

GetConfidence returns the Confidence field if non-nil, zero value otherwise.

### GetConfidenceOk

`func (o *StoreRequest) GetConfidenceOk() (*string, bool)`

GetConfidenceOk returns a tuple with the Confidence field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConfidence

`func (o *StoreRequest) SetConfidence(v string)`

SetConfidence sets Confidence field to given value.

### HasConfidence

`func (o *StoreRequest) HasConfidence() bool`

HasConfidence returns a boolean if a field has been set.

### SetConfidenceNil

`func (o *StoreRequest) SetConfidenceNil(b bool)`

 SetConfidenceNil sets the value for Confidence to be an explicit nil

### UnsetConfidence
`func (o *StoreRequest) UnsetConfidence()`

UnsetConfidence ensures that no value is present for Confidence, not even an explicit nil
### GetMeta

`func (o *StoreRequest) GetMeta() map[string]interface{}`

GetMeta returns the Meta field if non-nil, zero value otherwise.

### GetMetaOk

`func (o *StoreRequest) GetMetaOk() (*map[string]interface{}, bool)`

GetMetaOk returns a tuple with the Meta field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMeta

`func (o *StoreRequest) SetMeta(v map[string]interface{})`

SetMeta sets Meta field to given value.

### HasMeta

`func (o *StoreRequest) HasMeta() bool`

HasMeta returns a boolean if a field has been set.

### SetMetaNil

`func (o *StoreRequest) SetMetaNil(b bool)`

 SetMetaNil sets the value for Meta to be an explicit nil

### UnsetMeta
`func (o *StoreRequest) UnsetMeta()`

UnsetMeta ensures that no value is present for Meta, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


