package p2;

import com.opensymphony.xwork2.ActionSupport;

public class RegisterAction extends ActionSupport
{
	private String un;
	private String pwd;
	private String cpwd;
	public String getUn() {
		return un;
	}
	public void setUn(String un) {
		this.un = un;
	}
	public String getPwd() {
		return pwd;
	}
	public void setPwd(String pwd) {
		this.pwd = pwd;
	}
	public String getCpwd() {
		return cpwd;
	}
	public void setCpwd(String cpwd) {
		this.cpwd = cpwd;
	}
	
	public void validate()
	{
		if (un.length()==0) {
			
			addFieldError("un", "error in user name");
		}
		if (pwd.length()==0) {
			addFieldError("pwd", "password error");
		}
		if (cpwd.length()==0) {
			addFieldError("cpwd", "error in confrim password");
		}
		
	}

	public String execute()
	{
		System.out.println(un+" "+pwd+" "+ cpwd);
		return "s";
		
	}
}
