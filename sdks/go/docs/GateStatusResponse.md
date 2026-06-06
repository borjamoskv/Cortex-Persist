# GateStatusResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Policy** | **string** |  | 
**TimeoutSeconds** | **int32** |  | 
**Pending** | Pointer to **int32** |  | [optional] [default to 0]
**Approved** | Pointer to **int32** |  | [optional] [default to 0]
**Denied** | Pointer to **int32** |  | [optional] [default to 0]
**Expired** | Pointer to **int32** |  | [optional] [default to 0]
**Executed** | Pointer to **int32** |  | [optional] [default to 0]
**TotalAuditEntries** | Pointer to **int32** |  | [optional] [default to 0]

## Methods

### NewGateStatusResponse

`func NewGateStatusResponse(policy string, timeoutSeconds int32, ) *GateStatusResponse`

NewGateStatusResponse instantiates a new GateStatusResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewGateStatusResponseWithDefaults

`func NewGateStatusResponseWithDefaults() *GateStatusResponse`

NewGateStatusResponseWithDefaults instantiates a new GateStatusResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetPolicy

`func (o *GateStatusResponse) GetPolicy() string`

GetPolicy returns the Policy field if non-nil, zero value otherwise.

### GetPolicyOk

`func (o *GateStatusResponse) GetPolicyOk() (*string, bool)`

GetPolicyOk returns a tuple with the Policy field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPolicy

`func (o *GateStatusResponse) SetPolicy(v string)`

SetPolicy sets Policy field to given value.


### GetTimeoutSeconds

`func (o *GateStatusResponse) GetTimeoutSeconds() int32`

GetTimeoutSeconds returns the TimeoutSeconds field if non-nil, zero value otherwise.

### GetTimeoutSecondsOk

`func (o *GateStatusResponse) GetTimeoutSecondsOk() (*int32, bool)`

GetTimeoutSecondsOk returns a tuple with the TimeoutSeconds field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTimeoutSeconds

`func (o *GateStatusResponse) SetTimeoutSeconds(v int32)`

SetTimeoutSeconds sets TimeoutSeconds field to given value.


### GetPending

`func (o *GateStatusResponse) GetPending() int32`

GetPending returns the Pending field if non-nil, zero value otherwise.

### GetPendingOk

`func (o *GateStatusResponse) GetPendingOk() (*int32, bool)`

GetPendingOk returns a tuple with the Pending field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPending

`func (o *GateStatusResponse) SetPending(v int32)`

SetPending sets Pending field to given value.

### HasPending

`func (o *GateStatusResponse) HasPending() bool`

HasPending returns a boolean if a field has been set.

### GetApproved

`func (o *GateStatusResponse) GetApproved() int32`

GetApproved returns the Approved field if non-nil, zero value otherwise.

### GetApprovedOk

`func (o *GateStatusResponse) GetApprovedOk() (*int32, bool)`

GetApprovedOk returns a tuple with the Approved field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetApproved

`func (o *GateStatusResponse) SetApproved(v int32)`

SetApproved sets Approved field to given value.

### HasApproved

`func (o *GateStatusResponse) HasApproved() bool`

HasApproved returns a boolean if a field has been set.

### GetDenied

`func (o *GateStatusResponse) GetDenied() int32`

GetDenied returns the Denied field if non-nil, zero value otherwise.

### GetDeniedOk

`func (o *GateStatusResponse) GetDeniedOk() (*int32, bool)`

GetDeniedOk returns a tuple with the Denied field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDenied

`func (o *GateStatusResponse) SetDenied(v int32)`

SetDenied sets Denied field to given value.

### HasDenied

`func (o *GateStatusResponse) HasDenied() bool`

HasDenied returns a boolean if a field has been set.

### GetExpired

`func (o *GateStatusResponse) GetExpired() int32`

GetExpired returns the Expired field if non-nil, zero value otherwise.

### GetExpiredOk

`func (o *GateStatusResponse) GetExpiredOk() (*int32, bool)`

GetExpiredOk returns a tuple with the Expired field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetExpired

`func (o *GateStatusResponse) SetExpired(v int32)`

SetExpired sets Expired field to given value.

### HasExpired

`func (o *GateStatusResponse) HasExpired() bool`

HasExpired returns a boolean if a field has been set.

### GetExecuted

`func (o *GateStatusResponse) GetExecuted() int32`

GetExecuted returns the Executed field if non-nil, zero value otherwise.

### GetExecutedOk

`func (o *GateStatusResponse) GetExecutedOk() (*int32, bool)`

GetExecutedOk returns a tuple with the Executed field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetExecuted

`func (o *GateStatusResponse) SetExecuted(v int32)`

SetExecuted sets Executed field to given value.

### HasExecuted

`func (o *GateStatusResponse) HasExecuted() bool`

HasExecuted returns a boolean if a field has been set.

### GetTotalAuditEntries

`func (o *GateStatusResponse) GetTotalAuditEntries() int32`

GetTotalAuditEntries returns the TotalAuditEntries field if non-nil, zero value otherwise.

### GetTotalAuditEntriesOk

`func (o *GateStatusResponse) GetTotalAuditEntriesOk() (*int32, bool)`

GetTotalAuditEntriesOk returns a tuple with the TotalAuditEntries field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotalAuditEntries

`func (o *GateStatusResponse) SetTotalAuditEntries(v int32)`

SetTotalAuditEntries sets TotalAuditEntries field to given value.

### HasTotalAuditEntries

`func (o *GateStatusResponse) HasTotalAuditEntries() bool`

HasTotalAuditEntries returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


