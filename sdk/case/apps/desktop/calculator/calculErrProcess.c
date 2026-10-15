#include "calcul_play.h"
#include "float_simlib.h"

int stripleFloatPrecision(char *str, int num);
static int isop(char c);
int maxNumberCheck(const char *expstr);



void dealInputError(int errNo)
{
    switch (errNo)
    {
        case ERR_DOUBLE_OPERATOR:
        break;
        case ERR_MISSING_OPERATOR:
        //print_info(" ȱ�������\n");
        break;
        case ERR_MISSING_DECIAML:
        //print_info("С�������С������ȱʧ\n");
        break;
        case ERR_MSVALUE_NOT_VALID:
        //print_info("��ֵ�޷�����Ĵ���\n");
        break;
        default:
        //print_info("δ֪����\n");
        break;
    }
}

//�������ı���ʽ
//����޴�������1�����򷵻�0
int expressionCheck(char *expstr)
{
    int idx = 0;
    char c;
    char dststr[MAX_STR_LEN];
    char *p;

    if ((!expstr) || (strlen(expstr) > MAX_STR_LEN - 1))
    {
        return 0;
    }

    memset(dststr, 0, sizeof(dststr));
    p = expstr;
    //�ȳ�ȥ���пհ��ַ�
    c = *p;
    while (c != '\0')
    {
        if (c != ' ')
        {
            dststr[idx] = c;
            idx++;
        }
        p++;
        c = *p;
    }
    //ɨ�������﷨����

    //ȥ������С��λ�������ֻ�ܱ�����λ
    if(idx > MAX_STR_LEN)
    {
        return 0;	
    }
    if ((idx + 1) < MAX_STR_LEN)
    {
        memcpy(expstr, dststr, (unsigned int)(idx + 1));
    }
    stripleFloatPrecision(expstr, MAX_DECIMAL_LEN);
    //print_info("after expresssion check:  %s \n", expstr);

    if (maxNumberCheck(expstr) == 0) //����ʽ����
    {
        return 0;
    }
    else
    {
        return 1;
    }
}

/**
 *
 *������ʽ������С�����С������7λ�Ľض�
 */
int stripleFloatPrecision(char *str, int num)
{
    char *p = str;
    char *p2;
    char *tmpP;
    char c;
    char modifiedFlag = 0;
    int count = 0;
    char afterDecimal = 0; //������С����

    c = *p;
    while (c != '\0')
    {
        if (c == '.')
        {
            count = 0;
            afterDecimal = 1;
            p++;
            //continue;
            goto c_p_add;
        }
        
        if (afterDecimal == 1) //��С�����������������
        {
            if ((c == '0') || (c == '1') || (c == '2') || (c == '3') || (c == '4') ||  
                (c == '5') || (c == '6') || (c == '7') || (c == '8') || (c == '9') 
               )
            {
                count++;
            }
            else
            {
                afterDecimal = 0;
            }
        }
        
        if (count > num)
        {
            modifiedFlag = 1;
            p2 = p;
            tmpP = p;
            c = *p2;
            while (c != '\0')
            {
                if ((c == '+') || (c == '-') || (c == '*') || (c == '/'))
                {
                    break;
                }
                p2++;
                c = *p2;
            }
            
            while (*p2 != '\0')
            {
                *p = *p2;
                p++;
                p2++;
            }
            *p = '\0';
            
            //�ָ�p
            p = tmpP;
            afterDecimal = 0;
            count = 0;
            p--;
        }
        
        p++;
        
        c_p_add:    
        c = *p;
    }
    //print_info("after processing str:     %s \n", str);
    return modifiedFlag;
}

/**
 *
 *  ������޳������㷶Χ����������У�����0
 *  û���򷵻�1
 *
 */
int maxNumberCheck(const char *expstr)
{
    int startCount = 0;
    char c; 
      
    if (NULL == expstr)
    {
        return 0;
    }

    c = *expstr;
    while (c != '\0')
    {
        if (isop(c) == 1)
        {
            if (startCount > MAX_NUM_SUPPORT)
            {
                return 0;
            }
            else
            {
                startCount = 0;
                //continue;
                goto c_add;
            }
        }

        if (startCount > MAX_NUM_SUPPORT)
        {
            return 0;
        }
        if (c != '.')
        {
            startCount++;
        }
    
        c_add:    
        expstr++;
        c = *expstr;
    }
    
    if (startCount > MAX_NUM_SUPPORT)
    {
        return 0;
    }
    else
    {
        return 1;
    }
}

//����������������1
static int isop(char c)
{
    if ((c == '+') || (c == '-') || (c == '*') || (c == '/'))
    {
        return 1;
    }
    else
    {
        return 0;
    }
}

