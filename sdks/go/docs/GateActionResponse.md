# GateActionResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**ActionId** | **string** |  | 
**Level** | **string** |  | 
**Description** | **string** |  | 
**Command** | Pointer to **[]string** |  | [optional] 
**Project** | Pointer to **NullableString** |  | [optional] 
**Status** | **string** |  | 
**CreatedAt** | **string** |  | 
**ApprovedAt** | Pointer to **NullableString** |  | [optional] 
**OperatorId** | Pointer to **NullableString** |  | [optional] 

## Methods

### NewGateActionResponse

`func NewGateActionResponse(actionId string, level string, description string, status string, createdAt string, ) *GateActionResponse`

NewGateActionResponse instantiates a new GateActionResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewGateActionResponseWithDefaults

`func NewGateActionResponseWithDefaults() *GateActionResponse`

NewGateActionResponseWithDefaults instantiates a new GateActionResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetActionId

`func (o *GateActionResponse) GetActionId() string`

GetActionId returns the ActionId field if non-nil, zero value otherwise.

### GetActionIdOk

`func (o *GateActionResponse) GetActionIdOk() (*string, bool)`

GetActionIdOk returns a tuple with the ActionId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetActionId

`func (o *GateActionResponse) SetActionId(v string)`

SetActionId sets ActionId field to given value.


### GetLevel

`func (o *GateActionResponse) GetLevel() string`

GetLevel returns the Level field if non-nil, zero value otherwise.

### GetLevelOk

`func (o *GateActionResponse) GetLevelOk() (*string, bool)`

GetLevelOk returns a tuple with the Level field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetLevel

`func (o *GateActionResponse) SetLevel(v string)`

SetLevel sets Level field to given value.


### GetDescription

`func (o *GateActionResponse) GetDescription() string`

GetDescription returns the Description field if non-nil, zero value otherwise.

### GetDescriptionOk

`func (o *GateActionResponse) GetDescriptionOk() (*string, bool)`

GetDescriptionOk returns a tuple with the Description field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDescription

`func (o *GateActionResponse) SetDescription(v string)`

SetDescription sets Description field to given value.


### GetCommand

`func (o *GateActionResponse) GetCommand() []string`

GetCommand returns the Command field if non-nil, zero value otherwise.

### GetCommandOk

`func (o *GateActionResponse) GetCommandOk() (*[]string, bool)`

GetCommandOk returns a tuple with the Command field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCommand

`func (o *GateActionResponse) SetCommand(v []string)`

SetCommand sets Command field to given value.

### HasCommand

`func (o *GateActionResponse) HasCommand() bool`

HasCommand returns a boolean if a field has been set.

### SetCommandNil

`func (o *GateActionResponse) SetCommandNil(b bool)`

 SetCommandNil sets the value for Command to be an explicit nil

### UnsetCommand
`func (o *GateActionResponse) UnsetCommand()`

UnsetCommand ensures that no value is present for Command, not even an explicit nil
### GetProject

`func (o *GateActionResponse) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *GateActionResponse) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *GateActionResponse) SetProject(v string)`

SetProject sets Project field to given value.

### HasProject

`func (o *GateActionResponse) HasProject() bool`

HasProject returns a boolean if a field has been set.

### SetProjectNil

`func (o *GateActionResponse) SetProjectNil(b bool)`

 SetProjectNil sets the value for Project to be an explicit nil

### UnsetProject
`func (o *GateActionResponse) UnsetProject()`

UnsetProject ensures that no value is present for Project, not even an explicit nil
### GetStatus

`func (o *GateActionResponse) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *GateActionResponse) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *GateActionResponse) SetStatus(v string)`

SetStatus sets Status field to given value.


### GetCreatedAt

`func (o *GateActionResponse) GetCreatedAt() string`

GetCreatedAt returns the CreatedAt field if non-nil, zero value otherwise.

### GetCreatedAtOk

`func (o *GateActionResponse) GetCreatedAtOk() (*string, bool)`

GetCreatedAtOk returns a tuple with the CreatedAt field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetCreatedAt

`func (o *GateActionResponse) SetCreatedAt(v string)`

SetCreatedAt sets CreatedAt field to given value.


### GetApprovedAt

`func (o *GateActionResponse) GetApprovedAt() string`

GetApprovedAt returns the ApprovedAt field if non-nil, zero value otherwise.

### GetApprovedAtOk

`func (o *GateActionResponse) GetApprovedAtOk() (*string, bool)`

GetApprovedAtOk returns a tuple with the ApprovedAt field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetApprovedAt

`func (o *GateActionResponse) SetApprovedAt(v string)`

SetApprovedAt sets ApprovedAt field to given value.

### HasApprovedAt

`func (o *GateActionResponse) HasApprovedAt() bool`

HasApprovedAt returns a boolean if a field has been set.

### SetApprovedAtNil

`func (o *GateActionResponse) SetApprovedAtNil(b bool)`

 SetApprovedAtNil sets the value for ApprovedAt to be an explicit nil

### UnsetApprovedAt
`func (o *GateActionResponse) UnsetApprovedAt()`

UnsetApprovedAt ensures that no value is present for ApprovedAt, not even an explicit nil
### GetOperatorId

`func (o *GateActionResponse) GetOperatorId() string`

GetOperatorId returns the OperatorId field if non-nil, zero value otherwise.

### GetOperatorIdOk

`func (o *GateActionResponse) GetOperatorIdOk() (*string, bool)`

GetOperatorIdOk returns a tuple with the OperatorId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetOperatorId

`func (o *GateActionResponse) SetOperatorId(v string)`

SetOperatorId sets OperatorId field to given value.

### HasOperatorId

`func (o *GateActionResponse) HasOperatorId() bool`

HasOperatorId returns a boolean if a field has been set.

### SetOperatorIdNil

`func (o *GateActionResponse) SetOperatorIdNil(b bool)`

 SetOperatorIdNil sets the value for OperatorId to be an explicit nil

### UnsetOperatorId
`func (o *GateActionResponse) UnsetOperatorId()`

UnsetOperatorId ensures that no value is present for OperatorId, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


