# TrustProfileResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**AgentId** | **string** |  | 
**TrustScore** | **float32** |  | 
**Successes** | **int32** |  | 
**Failures** | **int32** |  | 
**TaintEvents** | **int32** |  | 
**LastSuccess** | Pointer to **NullableString** |  | [optional] 
**LastIncident** | Pointer to **NullableString** |  | [optional] 

## Methods

### NewTrustProfileResponse

`func NewTrustProfileResponse(agentId string, trustScore float32, successes int32, failures int32, taintEvents int32, ) *TrustProfileResponse`

NewTrustProfileResponse instantiates a new TrustProfileResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewTrustProfileResponseWithDefaults

`func NewTrustProfileResponseWithDefaults() *TrustProfileResponse`

NewTrustProfileResponseWithDefaults instantiates a new TrustProfileResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetAgentId

`func (o *TrustProfileResponse) GetAgentId() string`

GetAgentId returns the AgentId field if non-nil, zero value otherwise.

### GetAgentIdOk

`func (o *TrustProfileResponse) GetAgentIdOk() (*string, bool)`

GetAgentIdOk returns a tuple with the AgentId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAgentId

`func (o *TrustProfileResponse) SetAgentId(v string)`

SetAgentId sets AgentId field to given value.


### GetTrustScore

`func (o *TrustProfileResponse) GetTrustScore() float32`

GetTrustScore returns the TrustScore field if non-nil, zero value otherwise.

### GetTrustScoreOk

`func (o *TrustProfileResponse) GetTrustScoreOk() (*float32, bool)`

GetTrustScoreOk returns a tuple with the TrustScore field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTrustScore

`func (o *TrustProfileResponse) SetTrustScore(v float32)`

SetTrustScore sets TrustScore field to given value.


### GetSuccesses

`func (o *TrustProfileResponse) GetSuccesses() int32`

GetSuccesses returns the Successes field if non-nil, zero value otherwise.

### GetSuccessesOk

`func (o *TrustProfileResponse) GetSuccessesOk() (*int32, bool)`

GetSuccessesOk returns a tuple with the Successes field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSuccesses

`func (o *TrustProfileResponse) SetSuccesses(v int32)`

SetSuccesses sets Successes field to given value.


### GetFailures

`func (o *TrustProfileResponse) GetFailures() int32`

GetFailures returns the Failures field if non-nil, zero value otherwise.

### GetFailuresOk

`func (o *TrustProfileResponse) GetFailuresOk() (*int32, bool)`

GetFailuresOk returns a tuple with the Failures field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFailures

`func (o *TrustProfileResponse) SetFailures(v int32)`

SetFailures sets Failures field to given value.


### GetTaintEvents

`func (o *TrustProfileResponse) GetTaintEvents() int32`

GetTaintEvents returns the TaintEvents field if non-nil, zero value otherwise.

### GetTaintEventsOk

`func (o *TrustProfileResponse) GetTaintEventsOk() (*int32, bool)`

GetTaintEventsOk returns a tuple with the TaintEvents field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTaintEvents

`func (o *TrustProfileResponse) SetTaintEvents(v int32)`

SetTaintEvents sets TaintEvents field to given value.


### GetLastSuccess

`func (o *TrustProfileResponse) GetLastSuccess() string`

GetLastSuccess returns the LastSuccess field if non-nil, zero value otherwise.

### GetLastSuccessOk

`func (o *TrustProfileResponse) GetLastSuccessOk() (*string, bool)`

GetLastSuccessOk returns a tuple with the LastSuccess field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLastSuccess

`func (o *TrustProfileResponse) SetLastSuccess(v string)`

SetLastSuccess sets LastSuccess field to given value.

### HasLastSuccess

`func (o *TrustProfileResponse) HasLastSuccess() bool`

HasLastSuccess returns a boolean if a field has been set.

### SetLastSuccessNil

`func (o *TrustProfileResponse) SetLastSuccessNil(b bool)`

 SetLastSuccessNil sets the value for LastSuccess to be an explicit nil

### UnsetLastSuccess
`func (o *TrustProfileResponse) UnsetLastSuccess()`

UnsetLastSuccess ensures that no value is present for LastSuccess, not even an explicit nil
### GetLastIncident

`func (o *TrustProfileResponse) GetLastIncident() string`

GetLastIncident returns the LastIncident field if non-nil, zero value otherwise.

### GetLastIncidentOk

`func (o *TrustProfileResponse) GetLastIncidentOk() (*string, bool)`

GetLastIncidentOk returns a tuple with the LastIncident field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLastIncident

`func (o *TrustProfileResponse) SetLastIncident(v string)`

SetLastIncident sets LastIncident field to given value.

### HasLastIncident

`func (o *TrustProfileResponse) HasLastIncident() bool`

HasLastIncident returns a boolean if a field has been set.

### SetLastIncidentNil

`func (o *TrustProfileResponse) SetLastIncidentNil(b bool)`

 SetLastIncidentNil sets the value for LastIncident to be an explicit nil

### UnsetLastIncident
`func (o *TrustProfileResponse) UnsetLastIncident()`

UnsetLastIncident ensures that no value is present for LastIncident, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


