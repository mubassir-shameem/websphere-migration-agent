package com.ibm.websphere.sample;

import javax.ejb.Stateless;
import javax.ejb.EJB;
import com.ibm.websphere.security.auth.WSSubject;

@Stateless
public class SimpleEJB {

    public String sayHello(String name) {
        String user = WSSubject.getCallerPrincipal().getName();
        return "Hello " + name + " from " + user;
    }
}
