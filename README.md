# archivematica

This is the Wellcome Collection fork of [Archivematica](https://github.com/artefactual/archivematica).

See the original repo for documentation/development notes.
This README contains information specific to the Wellcome fork.



## How do we allow access to Archivematica?

We use Azure Active Directory (OpenID Connect) for authentication.
When somebody tries to log in to Archivematica, they are sent to an Active Directory login page first.
Once you're logged in with AD, you have access to Archivematica if and only if you have been authorised by an Archivematica admin.

If you want to give somebody access to Archivematica:

1.  Log in to the dashboard as an admin
2.  Select **Administration** from the top menu bar.
3.  In the sidebar, click **Users**.
4.  Click **Add New**.

    ![](screenshot_users_pane.png)

5.  Fill in the new user form.
    The two interesting fields:

    -   Email address must match their Wellcome email address, e.g. `a.chan@wellcome.ac.uk`
    -   The password can be anything, and they won't be using it in practice -- pick a suitably long random string and use that.
        If you want to generate passwords and you're comfortable on the command line, try running:

        ```
        python3 -c 'import secrets; print(secrets.token_hex())'
        ```

    Click **Create** when you're done.

To remove somebody's access, delete the user with their email address.
