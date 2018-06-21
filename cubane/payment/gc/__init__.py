import cubane.payment.gc.gocardless
"""
TODO: add variable direct debit and one time payment
"""


"""
Create Fixed Recurring Subscription
@return URL
"""
def create_subscription(amount, interval_length, interval_unit, merchant={}, additional_fields={}, sandbox=False):
    # settings up merchant
    setup_merchant(merchant, sandbox)

    # setting up additional fields (optional)
    name = additional_fields.get('name', None)
    description = additional_fields.get('description', None)
    user = additional_fields.get('user', {})
    start_at = additional_fields.get('start_at', None)
    expires_at = additional_fields.get('expires_at', None)
    interval_count = additional_fields.get('interval_count', None)
    setup_fee = additional_fields.get('setup_fee', None)
    state = additional_fields.get('state', None)

    url = cubane.payment.gc.gocardless.client.new_subscription_url(
        amount=amount,
        interval_length=interval_length,
        interval_unit=interval_unit,
        name=name,
        description=description,
        user=user,
        start_at=start_at,
        expires_at=expires_at,
        interval_count=interval_count,
        setup_fee=setup_fee,
        state=state)

    return url

"""
Confirm Subscription
"""
def confirm_payment(request, merchant={}, sandbox=False):
    # settings up merchant
    setup_merchant(merchant, sandbox)

    return cubane.payment.gc.gocardless.client.confirm_resource(request)


def setup_merchant(merchant, sandbox):
    # if sandbox we have to setup proper environment
    if sandbox:
        cubane.payment.gc.gocardless.environment = "sandbox"

    # setting up merchant (required)
    app_id = merchant.get('app_id', None)
    app_secret = merchant.get('app_secret', None)
    access_token = merchant.get('access_token', None)
    merchant_id = merchant.get('merchant_id', None)

    cubane.payment.gc.gocardless.set_details(
        app_id=app_id,
        app_secret=app_secret,
        access_token=access_token,
        merchant_id=merchant_id)
