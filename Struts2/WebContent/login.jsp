<%@ page language="java" contentType="text/html; charset=ISO-8859-1"
    pageEncoding="ISO-8859-1"%>
<%@taglib uri="/struts-tags" prefix="st" %>
<!DOCTYPE html>
<html>
<head>
<meta charset="ISO-8859-1">
<title>Insert title here</title>
</head>
<body>
<st:form action="login">
<st:textfield label="UserName" name ="un"></st:textfield>
<st:Password label="Password" name="pwd"></st:Password>
<st:submit value="login"></st:submit>
</st:form>
</body>
</html>