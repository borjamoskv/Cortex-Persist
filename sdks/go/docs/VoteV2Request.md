# VoteV2Request

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**AgentId** | **string** | UUID of the registered agent | 
**Vote** | **int32** | 1 to verify, -1 to dispute, 0 to remove | 
**Reason** | Pointer to **NullableString** |  | [optional] 
**Signature** | Pointer to **NullableString** | Optional cryptographic signature | [optional] 

## Methods

### NewVoteV2Request

`func NewVoteV2Request(agentId string, vote int32, ) *VoteV2Request`

NewVoteV2Request instantiates a new VoteV2Request object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewVoteV2RequestWithDefaults

`func NewVoteV2RequestWithDefaults() *VoteV2Request`

NewVoteV2RequestWithDefaults instantiates a new VoteV2Request object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetAgentId

`func (o *VoteV2Request) GetAgentId() string`

GetAgentId returns the AgentId field if non-nil, zero value otherwise.

### GetAgentIdOk

`func (o *VoteV2Request) GetAgentIdOk() (*string, bool)`

GetAgentIdOk returns a tuple with the AgentId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAgentId

`func (o *VoteV2Request) SetAgentId(v string)`

SetAgentId sets AgentId field to given value.


### GetVote

`func (o *VoteV2Request) GetVote() int32`

GetVote returns the Vote field if non-nil, zero value otherwise.

### GetVoteOk

`func (o *VoteV2Request) GetVoteOk() (*int32, bool)`

GetVoteOk returns a tuple with the Vote field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetVote

`func (o *VoteV2Request) SetVote(v int32)`

SetVote sets Vote field to given value.


### GetReason

`func (o *VoteV2Request) GetReason() string`

GetReason returns the Reason field if non-nil, zero value otherwise.

### GetReasonOk

`func (o *VoteV2Request) GetReasonOk() (*string, bool)`

GetReasonOk returns a tuple with the Reason field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetReason

`func (o *VoteV2Request) SetReason(v string)`

SetReason sets Reason field to given value.

### HasReason

`func (o *VoteV2Request) HasReason() bool`

HasReason returns a boolean if a field has been set.

### SetReasonNil

`func (o *VoteV2Request) SetReasonNil(b bool)`

 SetReasonNil sets the value for Reason to be an explicit nil

### UnsetReason
`func (o *VoteV2Request) UnsetReason()`

UnsetReason ensures that no value is present for Reason, not even an explicit nil
### GetSignature

`func (o *VoteV2Request) GetSignature() string`

GetSignature returns the Signature field if non-nil, zero value otherwise.

### GetSignatureOk

`func (o *VoteV2Request) GetSignatureOk() (*string, bool)`

GetSignatureOk returns a tuple with the Signature field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSignature

`func (o *VoteV2Request) SetSignature(v string)`

SetSignature sets Signature field to given value.

### HasSignature

`func (o *VoteV2Request) HasSignature() bool`

HasSignature returns a boolean if a field has been set.

### SetSignatureNil

`func (o *VoteV2Request) SetSignatureNil(b bool)`

 SetSignatureNil sets the value for Signature to be an explicit nil

### UnsetSignature
`func (o *VoteV2Request) UnsetSignature()`

UnsetSignature ensures that no value is present for Signature, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


