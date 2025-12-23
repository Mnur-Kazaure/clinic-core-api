class PatientCreateRequest(BaseModel):
    first_name: str
    last_name: str
    gender: Literal["MALE", "FEMALE", "OTHER"]
    date_of_birth: date | None
    occupation: str | None
    address: str | None
    phone: constr(min_length=7)
