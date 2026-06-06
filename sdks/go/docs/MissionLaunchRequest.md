# MissionLaunchRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Project** | **string** |  | 
**Goal** | **string** |  | 
**Formation** | Pointer to **string** |  | [optional] [default to "IRON_DOME"]
**Agents** | Pointer to **int32** |  | [optional] [default to 10]

## Methods

### NewMissionLaunchRequest

`func NewMissionLaunchRequest(project string, goal string, ) *MissionLaunchRequest`

NewMissionLaunchRequest instantiates a new MissionLaunchRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewMissionLaunchRequestWithDefaults

`func NewMissionLaunchRequestWithDefaults() *MissionLaunchRequest`

NewMissionLaunchRequestWithDefaults instantiates a new MissionLaunchRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetProject

`func (o *MissionLaunchRequest) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *MissionLaunchRequest) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *MissionLaunchRequest) SetProject(v string)`

SetProject sets Project field to given value.


### GetGoal

`func (o *MissionLaunchRequest) GetGoal() string`

GetGoal returns the Goal field if non-nil, zero value otherwise.

### GetGoalOk

`func (o *MissionLaunchRequest) GetGoalOk() (*string, bool)`

GetGoalOk returns a tuple with the Goal field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetGoal

`func (o *MissionLaunchRequest) SetGoal(v string)`

SetGoal sets Goal field to given value.


### GetFormation

`func (o *MissionLaunchRequest) GetFormation() string`

GetFormation returns the Formation field if non-nil, zero value otherwise.

### GetFormationOk

`func (o *MissionLaunchRequest) GetFormationOk() (*string, bool)`

GetFormationOk returns a tuple with the Formation field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFormation

`func (o *MissionLaunchRequest) SetFormation(v string)`

SetFormation sets Formation field to given value.

### HasFormation

`func (o *MissionLaunchRequest) HasFormation() bool`

HasFormation returns a boolean if a field has been set.

### GetAgents

`func (o *MissionLaunchRequest) GetAgents() int32`

GetAgents returns the Agents field if non-nil, zero value otherwise.

### GetAgentsOk

`func (o *MissionLaunchRequest) GetAgentsOk() (*int32, bool)`

GetAgentsOk returns a tuple with the Agents field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAgents

`func (o *MissionLaunchRequest) SetAgents(v int32)`

SetAgents sets Agents field to given value.

### HasAgents

`func (o *MissionLaunchRequest) HasAgents() bool`

HasAgents returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


