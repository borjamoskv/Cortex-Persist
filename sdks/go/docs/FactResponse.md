# FactResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Id** | **int32** |  | 
**Project** | **string** |  | 
**Content** | **string** |  | 
**FactType** | **string** |  | 
**Tags** | **[]string** |  | 
**CreatedAt** | **string** |  | 
**UpdatedAt** | **string** |  | 
**Confidence** | Pointer to [**NullableConfidence**](Confidence.md) |  | [optional] 
**ValidFrom** | Pointer to **NullableString** |  | [optional] 
**ValidUntil** | Pointer to **NullableString** |  | [optional] 
**Source** | Pointer to **NullableString** |  | [optional] 
**Meta** | Pointer to **map[string]interface{}** |  | [optional] 
**IsTombstoned** | Pointer to **bool** |  | [optional] [default to false]
**Hash** | Pointer to **NullableString** |  | [optional] 
**TxId** | Pointer to **NullableString** |  | [optional] 
**ConsensusScore** | Pointer to **NullableFloat32** |  | [optional] 

## Methods

### NewFactResponse

`func NewFactResponse(id int32, project string, content string, factType string, tags []string, createdAt string, updatedAt string, ) *FactResponse`

NewFactResponse instantiates a new FactResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewFactResponseWithDefaults

`func NewFactResponseWithDefaults() *FactResponse`

NewFactResponseWithDefaults instantiates a new FactResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetId

`func (o *FactResponse) GetId() int32`

GetId returns the Id field if non-nil, zero value otherwise.

### GetIdOk

`func (o *FactResponse) GetIdOk() (*int32, bool)`

GetIdOk returns a tuple with the Id field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetId

`func (o *FactResponse) SetId(v int32)`

SetId sets Id field to given value.


### GetProject

`func (o *FactResponse) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *FactResponse) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *FactResponse) SetProject(v string)`

SetProject sets Project field to given value.


### GetContent

`func (o *FactResponse) GetContent() string`

GetContent returns the Content field if non-nil, zero value otherwise.

### GetContentOk

`func (o *FactResponse) GetContentOk() (*string, bool)`

GetContentOk returns a tuple with the Content field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetContent

`func (o *FactResponse) SetContent(v string)`

SetContent sets Content field to given value.


### GetFactType

`func (o *FactResponse) GetFactType() string`

GetFactType returns the FactType field if non-nil, zero value otherwise.

### GetFactTypeOk

`func (o *FactResponse) GetFactTypeOk() (*string, bool)`

GetFactTypeOk returns a tuple with the FactType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFactType

`func (o *FactResponse) SetFactType(v string)`

SetFactType sets FactType field to given value.


### GetTags

`func (o *FactResponse) GetTags() []string`

GetTags returns the Tags field if non-nil, zero value otherwise.

### GetTagsOk

`func (o *FactResponse) GetTagsOk() (*[]string, bool)`

GetTagsOk returns a tuple with the Tags field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTags

`func (o *FactResponse) SetTags(v []string)`

SetTags sets Tags field to given value.


### GetCreatedAt

`func (o *FactResponse) GetCreatedAt() string`

GetCreatedAt returns the CreatedAt field if non-nil, zero value otherwise.

### GetCreatedAtOk

`func (o *FactResponse) GetCreatedAtOk() (*string, bool)`

GetCreatedAtOk returns a tuple with the CreatedAt field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCreatedAt

`func (o *FactResponse) SetCreatedAt(v string)`

SetCreatedAt sets CreatedAt field to given value.


### GetUpdatedAt

`func (o *FactResponse) GetUpdatedAt() string`

GetUpdatedAt returns the UpdatedAt field if non-nil, zero value otherwise.

### GetUpdatedAtOk

`func (o *FactResponse) GetUpdatedAtOk() (*string, bool)`

GetUpdatedAtOk returns a tuple with the UpdatedAt field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetUpdatedAt

`func (o *FactResponse) SetUpdatedAt(v string)`

SetUpdatedAt sets UpdatedAt field to given value.


### GetConfidence

`func (o *FactResponse) GetConfidence() Confidence`

GetConfidence returns the Confidence field if non-nil, zero value otherwise.

### GetConfidenceOk

`func (o *FactResponse) GetConfidenceOk() (*Confidence, bool)`

GetConfidenceOk returns a tuple with the Confidence field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConfidence

`func (o *FactResponse) SetConfidence(v Confidence)`

SetConfidence sets Confidence field to given value.

### HasConfidence

`func (o *FactResponse) HasConfidence() bool`

HasConfidence returns a boolean if a field has been set.

### SetConfidenceNil

`func (o *FactResponse) SetConfidenceNil(b bool)`

 SetConfidenceNil sets the value for Confidence to be an explicit nil

### UnsetConfidence
`func (o *FactResponse) UnsetConfidence()`

UnsetConfidence ensures that no value is present for Confidence, not even an explicit nil
### GetValidFrom

`func (o *FactResponse) GetValidFrom() string`

GetValidFrom returns the ValidFrom field if non-nil, zero value otherwise.

### GetValidFromOk

`func (o *FactResponse) GetValidFromOk() (*string, bool)`

GetValidFromOk returns a tuple with the ValidFrom field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetValidFrom

`func (o *FactResponse) SetValidFrom(v string)`

SetValidFrom sets ValidFrom field to given value.

### HasValidFrom

`func (o *FactResponse) HasValidFrom() bool`

HasValidFrom returns a boolean if a field has been set.

### SetValidFromNil

`func (o *FactResponse) SetValidFromNil(b bool)`

 SetValidFromNil sets the value for ValidFrom to be an explicit nil

### UnsetValidFrom
`func (o *FactResponse) UnsetValidFrom()`

UnsetValidFrom ensures that no value is present for ValidFrom, not even an explicit nil
### GetValidUntil

`func (o *FactResponse) GetValidUntil() string`

GetValidUntil returns the ValidUntil field if non-nil, zero value otherwise.

### GetValidUntilOk

`func (o *FactResponse) GetValidUntilOk() (*string, bool)`

GetValidUntilOk returns a tuple with the ValidUntil field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetValidUntil

`func (o *FactResponse) SetValidUntil(v string)`

SetValidUntil sets ValidUntil field to given value.

### HasValidUntil

`func (o *FactResponse) HasValidUntil() bool`

HasValidUntil returns a boolean if a field has been set.

### SetValidUntilNil

`func (o *FactResponse) SetValidUntilNil(b bool)`

 SetValidUntilNil sets the value for ValidUntil to be an explicit nil

### UnsetValidUntil
`func (o *FactResponse) UnsetValidUntil()`

UnsetValidUntil ensures that no value is present for ValidUntil, not even an explicit nil
### GetSource

`func (o *FactResponse) GetSource() string`

GetSource returns the Source field if non-nil, zero value otherwise.

### GetSourceOk

`func (o *FactResponse) GetSourceOk() (*string, bool)`

GetSourceOk returns a tuple with the Source field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSource

`func (o *FactResponse) SetSource(v string)`

SetSource sets Source field to given value.

### HasSource

`func (o *FactResponse) HasSource() bool`

HasSource returns a boolean if a field has been set.

### SetSourceNil

`func (o *FactResponse) SetSourceNil(b bool)`

 SetSourceNil sets the value for Source to be an explicit nil

### UnsetSource
`func (o *FactResponse) UnsetSource()`

UnsetSource ensures that no value is present for Source, not even an explicit nil
### GetMeta

`func (o *FactResponse) GetMeta() map[string]interface{}`

GetMeta returns the Meta field if non-nil, zero value otherwise.

### GetMetaOk

`func (o *FactResponse) GetMetaOk() (*map[string]interface{}, bool)`

GetMetaOk returns a tuple with the Meta field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMeta

`func (o *FactResponse) SetMeta(v map[string]interface{})`

SetMeta sets Meta field to given value.

### HasMeta

`func (o *FactResponse) HasMeta() bool`

HasMeta returns a boolean if a field has been set.

### SetMetaNil

`func (o *FactResponse) SetMetaNil(b bool)`

 SetMetaNil sets the value for Meta to be an explicit nil

### UnsetMeta
`func (o *FactResponse) UnsetMeta()`

UnsetMeta ensures that no value is present for Meta, not even an explicit nil
### GetIsTombstoned

`func (o *FactResponse) GetIsTombstoned() bool`

GetIsTombstoned returns the IsTombstoned field if non-nil, zero value otherwise.

### GetIsTombstonedOk

`func (o *FactResponse) GetIsTombstonedOk() (*bool, bool)`

GetIsTombstonedOk returns a tuple with the IsTombstoned field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetIsTombstoned

`func (o *FactResponse) SetIsTombstoned(v bool)`

SetIsTombstoned sets IsTombstoned field to given value.

### HasIsTombstoned

`func (o *FactResponse) HasIsTombstoned() bool`

HasIsTombstoned returns a boolean if a field has been set.

### GetHash

`func (o *FactResponse) GetHash() string`

GetHash returns the Hash field if non-nil, zero value otherwise.

### GetHashOk

`func (o *FactResponse) GetHashOk() (*string, bool)`

GetHashOk returns a tuple with the Hash field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetHash

`func (o *FactResponse) SetHash(v string)`

SetHash sets Hash field to given value.

### HasHash

`func (o *FactResponse) HasHash() bool`

HasHash returns a boolean if a field has been set.

### SetHashNil

`func (o *FactResponse) SetHashNil(b bool)`

 SetHashNil sets the value for Hash to be an explicit nil

### UnsetHash
`func (o *FactResponse) UnsetHash()`

UnsetHash ensures that no value is present for Hash, not even an explicit nil
### GetTxId

`func (o *FactResponse) GetTxId() string`

GetTxId returns the TxId field if non-nil, zero value otherwise.

### GetTxIdOk

`func (o *FactResponse) GetTxIdOk() (*string, bool)`

GetTxIdOk returns a tuple with the TxId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTxId

`func (o *FactResponse) SetTxId(v string)`

SetTxId sets TxId field to given value.

### HasTxId

`func (o *FactResponse) HasTxId() bool`

HasTxId returns a boolean if a field has been set.

### SetTxIdNil

`func (o *FactResponse) SetTxIdNil(b bool)`

 SetTxIdNil sets the value for TxId to be an explicit nil

### UnsetTxId
`func (o *FactResponse) UnsetTxId()`

UnsetTxId ensures that no value is present for TxId, not even an explicit nil
### GetConsensusScore

`func (o *FactResponse) GetConsensusScore() float32`

GetConsensusScore returns the ConsensusScore field if non-nil, zero value otherwise.

### GetConsensusScoreOk

`func (o *FactResponse) GetConsensusScoreOk() (*float32, bool)`

GetConsensusScoreOk returns a tuple with the ConsensusScore field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConsensusScore

`func (o *FactResponse) SetConsensusScore(v float32)`

SetConsensusScore sets ConsensusScore field to given value.

### HasConsensusScore

`func (o *FactResponse) HasConsensusScore() bool`

HasConsensusScore returns a boolean if a field has been set.

### SetConsensusScoreNil

`func (o *FactResponse) SetConsensusScoreNil(b bool)`

 SetConsensusScoreNil sets the value for ConsensusScore to be an explicit nil

### UnsetConsensusScore
`func (o *FactResponse) UnsetConsensusScore()`

UnsetConsensusScore ensures that no value is present for ConsensusScore, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


