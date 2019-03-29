# ssacl
SpectrumScale ACL Module

This module is to allow for the easy maintenance of ACLs in
the SpectrumScale file system.

ssacl - command line interface examples:

- List the ACLs on a file:

#-> ssacl --list ./testfile 
File: /data/acl/testfile
#owner:root
#group:root
user::rw-c
group::r---
other::r---

Let's say we want to apply the following ACL to the test file.
#-> cat acl.testfile 
#owner:root
#group:root
user::rw-c
group::r---
other::r---
mask::rw--
group:ckerner:r-x-

We will run it in verbose mode, to see what's going on
#-> ssacl --set -f acl.testfile -v testfile 
Processing: /data/acl/testfile setting ACL to file: acl.testfile
/usr/lpp/mmfs/bin/mmputacl -i acl.testfile /data/acl/testfile

Note that the ACL has been updated.
#-> ssacl --list testfile
File: /data/acl/testfile
#owner:root
#group:root
user::rw-c
group::r---
other::r---
mask::rw--
group:ckerner:r-x-  #effective: r---

Now, lets clear the ACL, and reset the permissions to 760:
#-> ssacl --clear -U=rwxc --GID=r-x- -O=---- testfile

#-> /ssacl --list testfile
File: /data/acl/testfile
#owner:root
#group:root
user::rwxc
group::r-x-
other::----

#> ls -l testfile
-rwxr-x--- 1 root root 0 Mar 28 09:15 testfile

