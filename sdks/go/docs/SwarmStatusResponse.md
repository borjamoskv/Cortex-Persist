# SwarmStatusResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**ActiveWorktrees** | **int32** |  | 
**TotalWorktrees** | **int32** |  | 
**AgentPids** | **[]int32** |  | 
**Timestamp** | **string** |  | 

## Methods

### NewSwarmStatusResponse

`func NewSwarmStatusResponse(activeWorktrees int32, totalWorktrees int32, agentPids []int32, timestamp string, ) *SwarmStatusResponse`

NewSwarmStatusResponse instantiates a new SwarmStatusResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewSwarmStatusResponseWithDefaults

`func NewSwarmStatusResponseWithDefaults() *SwarmStatusResponse`

NewSwarmStatusResponseWithDefaults instantiates a new SwarmStatusResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetActiveWorktrees

`func (o *SwarmStatusResponse) GetActiveWorktrees() int32`

GetActiveWorktrees returns the ActiveWorktrees field if non-nil, zero value otherwise.

### GetActiveWorktreesOk

`func (o *SwarmStatusResponse) GetActiveWorktreesOk() (*int32, bool)`

GetActiveWorktreesOk returns a tuple with the ActiveWorktrees field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetActiveWorktrees

`func (o *SwarmStatusResponse) SetActiveWorktrees(v int32)`

SetActiveWorktrees sets ActiveWorktrees field to given value.


### GetTotalWorktrees

`func (o *SwarmStatusResponse) GetTotalWorktrees() int32`

GetTotalWorktrees returns the TotalWorktrees field if non-nil, zero value otherwise.

### GetTotalWorktreesOk

`func (o *SwarmStatusResponse) GetTotalWorktreesOk() (*int32, bool)`

GetTotalWorktreesOk returns a tuple with the TotalWorktrees field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotalWorktrees

`func (o *SwarmStatusResponse) SetTotalWorktrees(v int32)`

SetTotalWorktrees sets TotalWorktrees field to given value.


### GetAgentPids

`func (o *SwarmStatusResponse) GetAgentPids() []int32`

GetAgentPids returns the AgentPids field if non-nil, zero value otherwise.

### GetAgentPidsOk

`func (o *SwarmStatusResponse) GetAgentPidsOk() (*[]int32, bool)`

GetAgentPidsOk returns a tuple with the AgentPids field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAgentPids

`func (o *SwarmStatusResponse) SetAgentPids(v []int32)`

SetAgentPids sets AgentPids field to given value.


### GetTimestamp

`func (o *SwarmStatusResponse) GetTimestamp() string`

GetTimestamp returns the Timestamp field if non-nil, zero value otherwise.

### GetTimestampOk

`func (o *SwarmStatusResponse) GetTimestampOk() (*string, bool)`

GetTimestampOk returns a tuple with the Timestamp field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTimestamp

`func (o *SwarmStatusResponse) SetTimestamp(v string)`

SetTimestamp sets Timestamp field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


