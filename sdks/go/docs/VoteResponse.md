# VoteResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**FactId** | **int32** |  | 
**Agent** | **string** |  | 
**Vote** | **int32** |  | 
**NewConsensusScore** | **float32** |  | 
**Confidence** | Pointer to [**NullableConfidence**](Confidence.md) |  | [optional] 
**Status** | Pointer to **string** |  | [optional] [default to "recorded"]

## Methods

### NewVoteResponse

`func NewVoteResponse(factId int32, agent string, vote int32, newConsensusScore float32, ) *VoteResponse`

NewVoteResponse instantiates a new VoteResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewVoteResponseWithDefaults

`func NewVoteResponseWithDefaults() *VoteResponse`

NewVoteResponseWithDefaults instantiates a new VoteResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetFactId

`func (o *VoteResponse) GetFactId() int32`

GetFactId returns the FactId field if non-nil, zero value otherwise.

### GetFactIdOk

`func (o *VoteResponse) GetFactIdOk() (*int32, bool)`

GetFactIdOk returns a tuple with the FactId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFactId

`func (o *VoteResponse) SetFactId(v int32)`

SetFactId sets FactId field to given value.


### GetAgent

`func (o *VoteResponse) GetAgent() string`

GetAgent returns the Agent field if non-nil, zero value otherwise.

### GetAgentOk

`func (o *VoteResponse) GetAgentOk() (*string, bool)`

GetAgentOk returns a tuple with the Agent field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAgent

`func (o *VoteResponse) SetAgent(v string)`

SetAgent sets Agent field to given value.


### GetVote

`func (o *VoteResponse) GetVote() int32`

GetVote returns the Vote field if non-nil, zero value otherwise.

### GetVoteOk

`func (o *VoteResponse) GetVoteOk() (*int32, bool)`

GetVoteOk returns a tuple with the Vote field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetVote

`func (o *VoteResponse) SetVote(v int32)`

SetVote sets Vote field to given value.


### GetNewConsensusScore

`func (o *VoteResponse) GetNewConsensusScore() float32`

GetNewConsensusScore returns the NewConsensusScore field if non-nil, zero value otherwise.

### GetNewConsensusScoreOk

`func (o *VoteResponse) GetNewConsensusScoreOk() (*float32, bool)`

GetNewConsensusScoreOk returns a tuple with the NewConsensusScore field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetNewConsensusScore

`func (o *VoteResponse) SetNewConsensusScore(v float32)`

SetNewConsensusScore sets NewConsensusScore field to given value.


### GetConfidence

`func (o *VoteResponse) GetConfidence() Confidence`

GetConfidence returns the Confidence field if non-nil, zero value otherwise.

### GetConfidenceOk

`func (o *VoteResponse) GetConfidenceOk() (*Confidence, bool)`

GetConfidenceOk returns a tuple with the Confidence field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetConfidence

`func (o *VoteResponse) SetConfidence(v Confidence)`

SetConfidence sets Confidence field to given value.

### HasConfidence

`func (o *VoteResponse) HasConfidence() bool`

HasConfidence returns a boolean if a field has been set.

### SetConfidenceNil

`func (o *VoteResponse) SetConfidenceNil(b bool)`

 SetConfidenceNil sets the value for Confidence to be an explicit nil

### UnsetConfidence
`func (o *VoteResponse) UnsetConfidence()`

UnsetConfidence ensures that no value is present for Confidence, not even an explicit nil
### GetStatus

`func (o *VoteResponse) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *VoteResponse) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *VoteResponse) SetStatus(v string)`

SetStatus sets Status field to given value.

### HasStatus

`func (o *VoteResponse) HasStatus() bool`

HasStatus returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


