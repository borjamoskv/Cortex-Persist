# StoreMemoryRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Project** | **string** |  | 
**Content** | **string** |  | 
**Type** | Pointer to **string** |  | [optional] [default to "knowledge"]
**Tags** | Pointer to **[]string** |  | [optional] 
**Source** | Pointer to **NullableString** |  | [optional] 
**Metadata** | Pointer to **map[string]interface{}** | Graph-RAG context (subgraph or related entities) | [optional] 
**ParentDecisionId** | Pointer to **NullableInt32** |  | [optional] 

## Methods

### NewStoreMemoryRequest

`func NewStoreMemoryRequest(project string, content string, ) *StoreMemoryRequest`

NewStoreMemoryRequest instantiates a new StoreMemoryRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewStoreMemoryRequestWithDefaults

`func NewStoreMemoryRequestWithDefaults() *StoreMemoryRequest`

NewStoreMemoryRequestWithDefaults instantiates a new StoreMemoryRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetProject

`func (o *StoreMemoryRequest) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *StoreMemoryRequest) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *StoreMemoryRequest) SetProject(v string)`

SetProject sets Project field to given value.


### GetContent

`func (o *StoreMemoryRequest) GetContent() string`

GetContent returns the Content field if non-nil, zero value otherwise.

### GetContentOk

`func (o *StoreMemoryRequest) GetContentOk() (*string, bool)`

GetContentOk returns a tuple with the Content field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetContent

`func (o *StoreMemoryRequest) SetContent(v string)`

SetContent sets Content field to given value.


### GetType

`func (o *StoreMemoryRequest) GetType() string`

GetType returns the Type field if non-nil, zero value otherwise.

### GetTypeOk

`func (o *StoreMemoryRequest) GetTypeOk() (*string, bool)`

GetTypeOk returns a tuple with the Type field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetType

`func (o *StoreMemoryRequest) SetType(v string)`

SetType sets Type field to given value.

### HasType

`func (o *StoreMemoryRequest) HasType() bool`

HasType returns a boolean if a field has been set.

### GetTags

`func (o *StoreMemoryRequest) GetTags() []string`

GetTags returns the Tags field if non-nil, zero value otherwise.

### GetTagsOk

`func (o *StoreMemoryRequest) GetTagsOk() (*[]string, bool)`

GetTagsOk returns a tuple with the Tags field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTags

`func (o *StoreMemoryRequest) SetTags(v []string)`

SetTags sets Tags field to given value.

### HasTags

`func (o *StoreMemoryRequest) HasTags() bool`

HasTags returns a boolean if a field has been set.

### GetSource

`func (o *StoreMemoryRequest) GetSource() string`

GetSource returns the Source field if non-nil, zero value otherwise.

### GetSourceOk

`func (o *StoreMemoryRequest) GetSourceOk() (*string, bool)`

GetSourceOk returns a tuple with the Source field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSource

`func (o *StoreMemoryRequest) SetSource(v string)`

SetSource sets Source field to given value.

### HasSource

`func (o *StoreMemoryRequest) HasSource() bool`

HasSource returns a boolean if a field has been set.

### SetSourceNil

`func (o *StoreMemoryRequest) SetSourceNil(b bool)`

 SetSourceNil sets the value for Source to be an explicit nil

### UnsetSource
`func (o *StoreMemoryRequest) UnsetSource()`

UnsetSource ensures that no value is present for Source, not even an explicit nil
### GetMetadata

`func (o *StoreMemoryRequest) GetMetadata() map[string]interface{}`

GetMetadata returns the Metadata field if non-nil, zero value otherwise.

### GetMetadataOk

`func (o *StoreMemoryRequest) GetMetadataOk() (*map[string]interface{}, bool)`

GetMetadataOk returns a tuple with the Metadata field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMetadata

`func (o *StoreMemoryRequest) SetMetadata(v map[string]interface{})`

SetMetadata sets Metadata field to given value.

### HasMetadata

`func (o *StoreMemoryRequest) HasMetadata() bool`

HasMetadata returns a boolean if a field has been set.

### SetMetadataNil

`func (o *StoreMemoryRequest) SetMetadataNil(b bool)`

 SetMetadataNil sets the value for Metadata to be an explicit nil

### UnsetMetadata
`func (o *StoreMemoryRequest) UnsetMetadata()`

UnsetMetadata ensures that no value is present for Metadata, not even an explicit nil
### GetParentDecisionId

`func (o *StoreMemoryRequest) GetParentDecisionId() int32`

GetParentDecisionId returns the ParentDecisionId field if non-nil, zero value otherwise.

### GetParentDecisionIdOk

`func (o *StoreMemoryRequest) GetParentDecisionIdOk() (*int32, bool)`

GetParentDecisionIdOk returns a tuple with the ParentDecisionId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetParentDecisionId

`func (o *StoreMemoryRequest) SetParentDecisionId(v int32)`

SetParentDecisionId sets ParentDecisionId field to given value.

### HasParentDecisionId

`func (o *StoreMemoryRequest) HasParentDecisionId() bool`

HasParentDecisionId returns a boolean if a field has been set.

### SetParentDecisionIdNil

`func (o *StoreMemoryRequest) SetParentDecisionIdNil(b bool)`

 SetParentDecisionIdNil sets the value for ParentDecisionId to be an explicit nil

### UnsetParentDecisionId
`func (o *StoreMemoryRequest) UnsetParentDecisionId()`

UnsetParentDecisionId ensures that no value is present for ParentDecisionId, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


