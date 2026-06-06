# SearchResult

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**FactId** | **int32** |  | 
**Project** | **string** |  | 
**Content** | **string** |  | 
**FactType** | **string** |  | 
**Score** | **float32** |  | 
**Tags** | **[]string** |  | 
**CreatedAt** | **string** |  | 
**UpdatedAt** | **string** |  | 
**Meta** | Pointer to **map[string]interface{}** |  | [optional] 
**Hash** | Pointer to **NullableString** |  | [optional] 
**Context** | Pointer to **map[string]interface{}** | Graph-RAG context (subgraph or related entities) | [optional] 

## Methods

### NewSearchResult

`func NewSearchResult(factId int32, project string, content string, factType string, score float32, tags []string, createdAt string, updatedAt string, ) *SearchResult`

NewSearchResult instantiates a new SearchResult object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSearchResultWithDefaults

`func NewSearchResultWithDefaults() *SearchResult`

NewSearchResultWithDefaults instantiates a new SearchResult object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetFactId

`func (o *SearchResult) GetFactId() int32`

GetFactId returns the FactId field if non-nil, zero value otherwise.

### GetFactIdOk

`func (o *SearchResult) GetFactIdOk() (*int32, bool)`

GetFactIdOk returns a tuple with the FactId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFactId

`func (o *SearchResult) SetFactId(v int32)`

SetFactId sets FactId field to given value.


### GetProject

`func (o *SearchResult) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *SearchResult) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *SearchResult) SetProject(v string)`

SetProject sets Project field to given value.


### GetContent

`func (o *SearchResult) GetContent() string`

GetContent returns the Content field if non-nil, zero value otherwise.

### GetContentOk

`func (o *SearchResult) GetContentOk() (*string, bool)`

GetContentOk returns a tuple with the Content field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetContent

`func (o *SearchResult) SetContent(v string)`

SetContent sets Content field to given value.


### GetFactType

`func (o *SearchResult) GetFactType() string`

GetFactType returns the FactType field if non-nil, zero value otherwise.

### GetFactTypeOk

`func (o *SearchResult) GetFactTypeOk() (*string, bool)`

GetFactTypeOk returns a tuple with the FactType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFactType

`func (o *SearchResult) SetFactType(v string)`

SetFactType sets FactType field to given value.


### GetScore

`func (o *SearchResult) GetScore() float32`

GetScore returns the Score field if non-nil, zero value otherwise.

### GetScoreOk

`func (o *SearchResult) GetScoreOk() (*float32, bool)`

GetScoreOk returns a tuple with the Score field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetScore

`func (o *SearchResult) SetScore(v float32)`

SetScore sets Score field to given value.


### GetTags

`func (o *SearchResult) GetTags() []string`

GetTags returns the Tags field if non-nil, zero value otherwise.

### GetTagsOk

`func (o *SearchResult) GetTagsOk() (*[]string, bool)`

GetTagsOk returns a tuple with the Tags field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTags

`func (o *SearchResult) SetTags(v []string)`

SetTags sets Tags field to given value.


### GetCreatedAt

`func (o *SearchResult) GetCreatedAt() string`

GetCreatedAt returns the CreatedAt field if non-nil, zero value otherwise.

### GetCreatedAtOk

`func (o *SearchResult) GetCreatedAtOk() (*string, bool)`

GetCreatedAtOk returns a tuple with the CreatedAt field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCreatedAt

`func (o *SearchResult) SetCreatedAt(v string)`

SetCreatedAt sets CreatedAt field to given value.


### GetUpdatedAt

`func (o *SearchResult) GetUpdatedAt() string`

GetUpdatedAt returns the UpdatedAt field if non-nil, zero value otherwise.

### GetUpdatedAtOk

`func (o *SearchResult) GetUpdatedAtOk() (*string, bool)`

GetUpdatedAtOk returns a tuple with the UpdatedAt field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUpdatedAt

`func (o *SearchResult) SetUpdatedAt(v string)`

SetUpdatedAt sets UpdatedAt field to given value.


### GetMeta

`func (o *SearchResult) GetMeta() map[string]interface{}`

GetMeta returns the Meta field if non-nil, zero value otherwise.

### GetMetaOk

`func (o *SearchResult) GetMetaOk() (*map[string]interface{}, bool)`

GetMetaOk returns a tuple with the Meta field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMeta

`func (o *SearchResult) SetMeta(v map[string]interface{})`

SetMeta sets Meta field to given value.

### HasMeta

`func (o *SearchResult) HasMeta() bool`

HasMeta returns a boolean if a field has been set.

### SetMetaNil

`func (o *SearchResult) SetMetaNil(b bool)`

 SetMetaNil sets the value for Meta to be an explicit nil

### UnsetMeta
`func (o *SearchResult) UnsetMeta()`

UnsetMeta ensures that no value is present for Meta, not even an explicit nil
### GetHash

`func (o *SearchResult) GetHash() string`

GetHash returns the Hash field if non-nil, zero value otherwise.

### GetHashOk

`func (o *SearchResult) GetHashOk() (*string, bool)`

GetHashOk returns a tuple with the Hash field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetHash

`func (o *SearchResult) SetHash(v string)`

SetHash sets Hash field to given value.

### HasHash

`func (o *SearchResult) HasHash() bool`

HasHash returns a boolean if a field has been set.

### SetHashNil

`func (o *SearchResult) SetHashNil(b bool)`

 SetHashNil sets the value for Hash to be an explicit nil

### UnsetHash
`func (o *SearchResult) UnsetHash()`

UnsetHash ensures that no value is present for Hash, not even an explicit nil
### GetContext

`func (o *SearchResult) GetContext() map[string]interface{}`

GetContext returns the Context field if non-nil, zero value otherwise.

### GetContextOk

`func (o *SearchResult) GetContextOk() (*map[string]interface{}, bool)`

GetContextOk returns a tuple with the Context field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetContext

`func (o *SearchResult) SetContext(v map[string]interface{})`

SetContext sets Context field to given value.

### HasContext

`func (o *SearchResult) HasContext() bool`

HasContext returns a boolean if a field has been set.

### SetContextNil

`func (o *SearchResult) SetContextNil(b bool)`

 SetContextNil sets the value for Context to be an explicit nil

### UnsetContext
`func (o *SearchResult) UnsetContext()`

UnsetContext ensures that no value is present for Context, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


